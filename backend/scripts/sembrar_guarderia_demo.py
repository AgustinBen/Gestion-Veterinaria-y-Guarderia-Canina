"""Llena el cupo público mínimo de hoy con mascotas de sembrar_demo.

Uso desde backend/:
    .\\.venv\\Scripts\\python.exe scripts\\sembrar_demo.py
    .\\.venv\\Scripts\\python.exe scripts\\sembrar_guarderia_demo.py

Cada reserva cubre Día y Noche, por lo que la misma cantidad de mascotas ocupa
una plaza en cada franja. Los importes se eligen de cargos demo existentes y
las señas se generan en centavos. Claves e importes son reproducibles para
permitir ejecuciones idempotentes.
"""

from __future__ import annotations

import random
import sys
from datetime import date

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.core.parametros import get_param
from app.modules.cobros import service as cobros_service
from app.modules.guarderia import seed as guarderia_seed
from app.modules.guarderia import service as guarderia_service
from app.modules.guarderia.franjas import Franja
from app.modules.guarderia.schemas import (
    CuidadoExtraAnimal,
    ReservaCrear,
    ReservaSenaCrear,
)
from app.modules.identidad import service as identidad_service
from app.modules.identidad.permisos import Rol
from app.modules.identidad.schemas import UsuarioPublico
from app.modules.padron import service as padron_service

try:
    from scripts.sembrar_demo import CARGOS, MASCOTAS, TUTORES
except ModuleNotFoundError:
    from sembrar_demo import CARGOS, MASCOTAS, TUTORES


class SeedError(Exception):
    """Faltan datos demo necesarios para crear las reservas."""


def _usuario_registrador(db: Session) -> UsuarioPublico:
    activos = [
        usuario
        for usuario in identidad_service.listar_usuarios(db)
        if usuario.activo
    ]
    if not activos:
        raise SeedError(
            "No hay usuarios activos. Creá el Dueño con "
            "'python scripts/crear_dueno.py'."
        )
    duenios = [usuario for usuario in activos if usuario.rol is Rol.DUENIO]
    return (duenios or activos)[0]


def _resolver_tutor_y_paciente(
    db: Session,
    mascota_clave: str,
) -> tuple[int, int, str]:
    mascotas = {mascota.clave: mascota for mascota in MASCOTAS}
    tutores = {tutor.clave: tutor for tutor in TUTORES}
    mascota = mascotas.get(mascota_clave)
    if mascota is None:
        raise SeedError(f"No existe la mascota demo '{mascota_clave}'.")
    tutor = tutores.get(mascota.tutor)
    if tutor is None:
        raise SeedError(f"No existe el tutor demo de '{mascota.nombre}'.")

    personas = padron_service.buscar_personas(db, dni=tutor.dni)
    persona = next((item for item in personas if item.dni == tutor.dni), None)
    if persona is None:
        raise SeedError(
            "No se encontró el tutor demo. Ejecutá "
            "'python scripts/sembrar_demo.py' primero."
        )

    paciente = next(
        (
            item
            for item in padron_service.pacientes_de_persona(db, persona.id)
            if item.nombre.strip().casefold() == mascota.nombre.strip().casefold()
        ),
        None,
    )
    if paciente is None:
        raise SeedError(
            f"No se encontró '{mascota.nombre}' vinculada a su tutor demo. "
            "Ejecutá 'python scripts/sembrar_demo.py' primero."
        )
    detalle = padron_service.obtener_paciente(db, paciente.id)
    if detalle is None or not detalle.activo:
        raise SeedError(f"La mascota demo '{mascota.nombre}' no está activa.")
    return persona.id, paciente.id, mascota.nombre


def _monto_y_sena(
    fecha: date,
    desde_franja: Franja,
    hasta_franja: Franja,
    mascota_clave: str,
) -> tuple[int, int]:
    montos_demo = [
        cargo.total_centavos
        for cargo in CARGOS
        if cargo.referencia.startswith("RES-")
    ]
    if not montos_demo:
        raise SeedError("No hay importes de guardería en sembrar_demo.")

    generador = random.Random(
        f"guarderia-demo:{fecha.isoformat()}:"
        f"{desde_franja.value}:{hasta_franja.value}:{mascota_clave}"
    )
    total_centavos = generador.choice(montos_demo)
    sena_centavos = generador.randint(1, total_centavos // 100) * 100
    return total_centavos, sena_centavos


def sembrar_reserva_demo(
    db: Session,
    *,
    fecha: date,
    desde_franja: Franja,
    hasta_franja: Franja,
    mascota_clave: str,
    tutor_persona_id: int,
    paciente_id: int,
    usuario: UsuarioPublico,
) -> tuple[int, int, int]:
    total_centavos, sena_centavos = _monto_y_sena(
        fecha, desde_franja, hasta_franja, mascota_clave
    )
    clave = (
        f"seed_guarderia_demo:{fecha.isoformat()}:"
        f"{mascota_clave}:{desde_franja.value}:{hasta_franja.value}"
    )
    solicitud = ReservaCrear(
        tutor_persona_id=tutor_persona_id,
        paciente_ids=[paciente_id],
        desde_fecha=fecha,
        desde_franja=desde_franja,
        hasta_fecha=fecha,
        hasta_franja=hasta_franja,
        cuidados_extras=[
            CuidadoExtraAnimal(
                paciente_id=paciente_id,
                cuidados_extras=False,
            )
        ],
        total_centavos=total_centavos,
    )
    reserva, _ = guarderia_service.crear_reserva(
        db,
        solicitud,
        clave_idempotencia=clave,
        usuario_id=usuario.id,
    )
    guarderia_service.registrar_sena(
        db,
        reserva.id,
        ReservaSenaCrear(monto_centavos=sena_centavos, medio="EFECTIVO"),
        clave_idempotencia=f"{clave}:sena",
        usuario_id=usuario.id,
        empleado_id=usuario.empleado_id,
    )
    return reserva.id, total_centavos, sena_centavos


def main() -> int:
    fecha = date.today()
    try:
        with SessionLocal() as db:
            guarderia_seed.sembrar_parametros(db)
            usuario = _usuario_registrador(db)
            cupo_minimo = get_param(db, "guarderia.cupo_minimo")
            plazas_emergencia = get_param(db, "guarderia.plazas_emergencia")
            if (
                type(cupo_minimo) is not int
                or type(plazas_emergencia) is not int
                or cupo_minimo <= plazas_emergencia
            ):
                raise SeedError("La configuración mínima de cupo no es válida.")
            objetivo_publico = cupo_minimo - plazas_emergencia
            disponibilidad_dia = guarderia_service.calcular_disponibilidad(
                db, fecha, Franja.DIA
            )
            disponibilidad_noche = guarderia_service.calcular_disponibilidad(
                db, fecha, Franja.NOCHE
            )
            faltan_dia = max(objetivo_publico - disponibilidad_dia.ocupado, 0)
            faltan_noche = max(objetivo_publico - disponibilidad_noche.ocupado, 0)

            print(
                f"Fecha: {fecha.isoformat()} · registra: {usuario.username} · "
                f"objetivo público mínimo: {objetivo_publico} mascotas por franja"
            )

            tutores_usados: set[str] = set()
            for mascota in MASCOTAS:
                if faltan_dia == 0 and faltan_noche == 0:
                    break
                if mascota.tutor in tutores_usados:
                    continue
                mascota_clave = mascota.clave
                tutor_id, paciente_id, nombre = _resolver_tutor_y_paciente(
                    db, mascota_clave
                )
                tutores_usados.add(mascota.tutor)
                if faltan_dia > 0 and faltan_noche > 0:
                    desde_franja, hasta_franja = Franja.DIA, Franja.NOCHE
                elif faltan_dia > 0:
                    desde_franja = hasta_franja = Franja.DIA
                else:
                    desde_franja = hasta_franja = Franja.NOCHE

                resultado = guarderia_service.verificar_cupo(
                    db,
                    [paciente_id],
                    (fecha, desde_franja),
                    (fecha, hasta_franja),
                )
                if resultado.codigo != "DISPONIBLE":
                    continue
                reserva_id, total, sena = sembrar_reserva_demo(
                    db,
                    fecha=fecha,
                    desde_franja=desde_franja,
                    hasta_franja=hasta_franja,
                    mascota_clave=mascota_clave,
                    tutor_persona_id=tutor_id,
                    paciente_id=paciente_id,
                    usuario=usuario,
                )
                if desde_franja == Franja.DIA and hasta_franja == Franja.NOCHE:
                    faltan_dia -= 1
                    faltan_noche -= 1
                elif desde_franja == Franja.DIA:
                    faltan_dia -= 1
                else:
                    faltan_noche -= 1
                print(
                    f"  Reserva #{reserva_id}: {nombre} · "
                    f"{desde_franja.value}–{hasta_franja.value} · "
                    f"total {total} centavos · seña {sena} centavos"
                )
            if faltan_dia or faltan_noche:
                raise SeedError(
                    "No hay suficientes mascotas demo disponibles para completar "
                    f"el objetivo; faltan {faltan_dia} plazas de Día y "
                    f"{faltan_noche} de Noche."
                )
    except (
        SeedError,
        guarderia_service.ReservaInvalida,
        guarderia_service.ReservaCupoConflicto,
        guarderia_service.IdempotenciaReservaConflicto,
        guarderia_service.EstadoReservaInvalido,
        cobros_service.CobrosError,
        padron_service.DatosInvalidos,
        padron_service.PacienteNoEncontrado,
        padron_service.PersonaNoEncontrada,
        SQLAlchemyError,
    ) as exc:
        print(f"No se pudo sembrar la guardería demo: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
