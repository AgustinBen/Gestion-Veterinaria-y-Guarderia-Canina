"""Seed de datos de demostración del local.

Uso:
    python scripts/sembrar_demo.py

Es idempotente: busca tutores por DNI, mascotas por nombre y cargos por
referencia (o concepto) antes de crear. Los pagos usan una clave de
idempotencia determinística por cargo. Escribe solo a través del ``service.py``
público de padrón y cobros, sin tocar ``models``/``repository`` ajenos.

Alcance:
- Los datos clínicos se cargan solo como cargo + pagos: fecha, servicio y
  montos. No se guardan diagnóstico, medicación ni veterinario tratante porque
  el módulo clínica todavía no existe.
- El módulo guardería tampoco existe: las fechas, la modalidad y los cuidados
  quedan documentados acá, pero en la base solo se persiste el concepto y el
  total del cargo.
- "Transferencia pendiente" y "debe total" se cargan como deuda (sin pago).
- Cuando el texto no aclara el medio de un pago cobrado, se usa efectivo.
"""

from __future__ import annotations

import calendar
import sys
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.core.db import SessionLocal
from app.modules.cobros import dinero
from app.modules.cobros import seed as cobros_seed
from app.modules.cobros import service as cobros_service
from app.modules.identidad import service as identidad_service
from app.modules.identidad.permisos import Rol
from app.modules.identidad.schemas import UsuarioPublico
from app.modules.padron import seed as padron_seed
from app.modules.padron import service as padron_service
from app.modules.padron.schemas import (
    DomicilioNuevo,
    PacienteActualizar,
    PacienteNuevo,
    PersonaNueva,
    RazaNueva,
)

REFERENCIA_SEED = "seed_demo"

EFECTIVO = "EFECTIVO"
DEBITO = "DEBITO"
TRANSFERENCIA = "TRANSFERENCIA"
MERCADO_PAGO = "MERCADO_PAGO"


class SeedError(Exception):
    """Falta un dato base para poder sembrar."""


@dataclass(frozen=True)
class TutorDemo:
    clave: str
    nombre: str
    apellido: str
    dni: str
    telefono: str | None
    calle: str | None = None
    localidad: str | None = None
    piso: str | None = None
    departamento: str | None = None


@dataclass(frozen=True)
class MascotaDemo:
    clave: str
    tutor: str
    nombre: str
    especie: str
    raza: str | None
    edad_meses: int | None
    peso_kg: str | None
    tamanio: str | None = None


@dataclass(frozen=True)
class PagoDemo:
    monto_centavos: int
    medio: str
    es_sena: bool = False


@dataclass(frozen=True)
class AjusteDemo:
    nuevo_total_centavos: int
    motivo: str


@dataclass(frozen=True)
class CargoDemo:
    referencia: str
    mascota: str
    concepto: str
    total_centavos: int
    fecha: date
    pagos: tuple[PagoDemo, ...] = ()
    ajuste: AjusteDemo | None = None
    detalle: str | None = None
    cuidados: str | None = None

    @property
    def numero(self) -> int:
        return int(self.referencia.split("-", 1)[1])


# Los DNI de los tutores nuevos son ficticios y solo existen para la demo.
TUTORES: tuple[TutorDemo, ...] = (
    TutorDemo(
        "valeria",
        "Valeria",
        "Gomez",
        "30000001",
        "11 4455-8899",
        "Av. Cabildo 1500",
        "Belgrano",
        piso="4",
    ),
    TutorDemo(
        "esteban",
        "Esteban",
        "Morales",
        "30000002",
        "011 6677-2233",
        "Thames 2200",
        "Palermo",
    ),
    TutorDemo(
        "mariana",
        "Mariana",
        "Rios",
        "30000003",
        "011 4890-1122",
        "Av. Santa Fe 3200",
        "CABA",
        departamento="2B",
    ),
    TutorDemo("carlos", "Carlos", "Tevez", "55555555", "+54 9 11 3322 1100"),
    TutorDemo(
        "luciana",
        "Luciana",
        "Fernandez",
        "30000004",
        "15-9988-4455",
        "Av. Rivadavia 6500",
        "CABA",
    ),
    # "Sin teléfono (dejó mail)": no hay campo de email en padrón.
    TutorDemo("pablo", "Pablo", "Echarri", "30000005", None),
    TutorDemo("martin", "Martin", "Palermo", "30000006", "11-2233-4455"),
    TutorDemo("romina", "Romina", "Gaetani", "30000007", "0341-155443322"),
    TutorDemo(
        "claudio",
        "Claudio",
        "Rossi",
        "30000008",
        "+5491177889900",
        "Laprida 800",
        "Recoleta",
    ),
)

MASCOTAS: tuple[MascotaDemo, ...] = (
    MascotaDemo("firulais", "valeria", "Firulais", "Perro", "Labrador", 48, "28.5"),
    MascotaDemo("rocco", "esteban", "Rocco", "Perro", "Bulldog Francés", 30, "12.2"),
    MascotaDemo("luna", "mariana", "Luna", "Gato", "Siamés", 12, "3.5"),
    MascotaDemo("milo", "mariana", "Milo", "Gato", "Común", 6, "2.8"),
    MascotaDemo("pampa", "carlos", "Pampa", "Perro", "Ovejero Alemán", 84, "34.0"),
    MascotaDemo("simon", "luciana", "Simon", "Perro", "Caniche Toy", 132, "4.2"),
    MascotaDemo("chicho", "pablo", "Chicho", "Perro", "Mestizo", 36, "15", "Mediano"),
    MascotaDemo("titan", "martin", "Titan", "Perro", "Doberman", 60, "38.5"),
    MascotaDemo("lola", "romina", "Lola", "Perro", "Caniche", 8, "3.9"),
    MascotaDemo(
        "rocco_jr", "esteban", "Rocco Jr.", "Perro", "Bulldog Francés", 3, "2.1"
    ),
    MascotaDemo("boby", "claudio", "Boby", "Perro", "Mestizo", 144, "18"),
)

CARGOS: tuple[CargoDemo, ...] = (
    # Atenciones clínicas: solo la parte cobrable (sin historia clínica).
    CargoDemo(
        "AT-501",
        "firulais",
        "Consulta General 10/05/2026",
        1_850_000,
        date(2026, 5, 10),
        (PagoDemo(1_850_000, EFECTIVO),),
        detalle="Vómitos tras comer pasto. Reliveran y dieta blanda 48 hs.",
    ),
    CargoDemo(
        "AT-502",
        "rocco",
        "Vacunación 11/05/2026",
        2_400_000,
        date(2026, 5, 11),
        (PagoDemo(2_400_000, MERCADO_PAGO),),
        detalle="Antirrábica anual. Próxima en 2027.",
    ),
    CargoDemo(
        "AT-503",
        "luna",
        "Urgencia 12/05/2026",
        3_700_000,
        date(2026, 5, 12),
        (PagoDemo(2_700_000, EFECTIVO),),
        detalle="Placa $15.000 + atención $22.000. Quedó debiendo $10.000.",
    ),
    CargoDemo(
        "AT-504",
        "milo",
        "Castración 14/05/2026",
        6_500_000,
        date(2026, 5, 14),
        (
            PagoDemo(3_000_000, EFECTIVO, es_sena=True),
            PagoDemo(3_500_000, TRANSFERENCIA),
        ),
        detalle="Orquiectomía. Seña previa $30.000 y saldo $35.000.",
    ),
    CargoDemo(
        "AT-505",
        "pampa",
        "Control / Vacuna 15/05/2026",
        2_800_000,
        date(2026, 5, 15),
        (PagoDemo(2_800_000, DEBITO),),
        detalle="Séxtuple anual y corte de uñas. Se usó bozal.",
    ),
    # Base $18.000 bonificada al 50%: se registra el ajuste (RN-22).
    CargoDemo(
        "AT-506",
        "simon",
        "Consulta Geriátrica 16/05/2026",
        1_800_000,
        date(2026, 5, 16),
        ajuste=AjusteDemo(900_000, "Bonificación 50% cliente frecuente (dato de seed)"),
        detalle="Soplo cardíaco grado II. Enalapril de por vida.",
    ),
    CargoDemo(
        "AT-507",
        "chicho",
        "Desparasitación 18/05/2026",
        850_000,
        date(2026, 5, 18),
        (PagoDemo(850_000, EFECTIVO),),
        detalle="Total Full CG masticable.",
    ),
    CargoDemo(
        "AT-508",
        "titan",
        "Control herida 19/05/2026",
        1_400_000,
        date(2026, 5, 19),
        detalle="Curación por pelea. Amoxicilina. Debe $14.000.",
    ),
    CargoDemo(
        "AT-509",
        "lola",
        "Vacuna séxtuple 20/05/2026",
        2_100_000,
        date(2026, 5, 20),
        (PagoDemo(2_100_000, EFECTIVO),),
        detalle="Segunda dosis de cachorra. Libreta firmada.",
    ),
    CargoDemo(
        "AT-510",
        "boby",
        "Consulta dolor cadera 21/05/2026",
        3_200_000,
        date(2026, 5, 21),
        (PagoDemo(1_600_000, EFECTIVO),),
        detalle="Artritis avanzada. Corticoide y glucosamina. Pagó la mitad.",
    ),
    # Guardería: fechas, modalidad y cuidados quedan en el concepto/dato,
    # porque el módulo guardería todavía no existe.
    CargoDemo(
        "RES-101",
        "firulais",
        "Guardería Nocturna (3 noches) 15/05/2026 al 18/05/2026",
        4_500_000,
        date(2026, 5, 15),
        (PagoDemo(2_000_000, EFECTIVO, es_sena=True),),
        cuidados="No juntar con perros machos chicos.",
    ),
    CargoDemo(
        "RES-102",
        "rocco",
        "Pase diario completo 15/05/2026 al 16/05/2026",
        1_200_000,
        date(2026, 5, 15),
        (PagoDemo(1_200_000, EFECTIVO),),
        cuidados="Toma medicación a las 20 hs con comida.",
    ),
    CargoDemo(
        "RES-103",
        "pampa",
        "Guardería 15/05/2026 al 17/05/2026",
        3_200_000,
        date(2026, 5, 15),
        cuidados="Socializa bien, duerme adentro.",
    ),
    CargoDemo(
        "RES-104",
        "chicho",
        "Estadía semanal 16/05/2026 al 20/05/2026",
        9_500_000,
        date(2026, 5, 16),
        (PagoDemo(9_500_000, EFECTIVO),),
        cuidados="Miedo a ruidos fuertes.",
    ),
    CargoDemo(
        "RES-105",
        "titan",
        "Medio día tarde 16/05/2026",
        800_000,
        date(2026, 5, 16),
        (PagoDemo(800_000, EFECTIVO),),
        cuidados="Muy dominante en el patio.",
    ),
    CargoDemo(
        "RES-106",
        "rocco_jr",
        "Guardería cachorros 16/05/2026",
        1_500_000,
        date(2026, 5, 16),
        (PagoDemo(500_000, EFECTIVO, es_sena=True),),
        cuidados="Cuidado con escapes.",
    ),
    CargoDemo(
        "RES-107",
        "simon",
        "Estadía prolongada 18/05/2026 al 22/05/2026",
        6_800_000,
        date(2026, 5, 18),
        cuidados="No camina mucho (abuelo).",
    ),
    CargoDemo(
        "RES-108",
        "lola",
        "Día completo 19/05/2026",
        1_400_000,
        date(2026, 5, 19),
        (PagoDemo(1_400_000, MERCADO_PAGO),),
        cuidados="Súper sociable y juguetona.",
    ),
    CargoDemo(
        "RES-109",
        "firulais",
        "Guardería 5 noches 20/05/2026 al 25/05/2026",
        7_500_000,
        date(2026, 5, 20),
        (PagoDemo(3_000_000, EFECTIVO, es_sena=True),),
        cuidados="Dieta especial Pro Plan Gastrointestinal.",
    ),
    CargoDemo(
        "RES-110",
        "milo",
        "Guardería felina 20/05/2026 al 22/05/2026",
        3_600_000,
        date(2026, 5, 20),
        (PagoDemo(3_600_000, EFECTIVO),),
        cuidados="Jaula individual para gato.",
    ),
)


def _elegir_usuario(db) -> UsuarioPublico:
    """Usuario que queda como creador de cargos y pagos."""
    activos = [usuario for usuario in identidad_service.listar_usuarios(db) if usuario.activo]
    if not activos:
        raise SeedError(
            "No hay usuarios activos. Creá el Dueño con 'python scripts/crear_dueno.py'."
        )
    duenios = [usuario for usuario in activos if usuario.rol is Rol.DUENIO]
    return (duenios or activos)[0]


def _fecha_nacimiento_aprox(meses: int | None) -> date | None:
    """Convierte la edad aproximada en fecha de nacimiento (RN-09)."""
    if meses is None:
        return None
    hoy = date.today()
    indice = hoy.year * 12 + (hoy.month - 1) - meses
    anio, mes_base = divmod(indice, 12)
    mes = mes_base + 1
    dia = min(hoy.day, calendar.monthrange(anio, mes)[1])
    return date(anio, mes, dia)


def _resolver_tutores(db) -> tuple[dict[str, int], int]:
    ids: dict[str, int] = {}
    creados = 0
    for tutor in TUTORES:
        existentes = padron_service.buscar_personas(db, dni=tutor.dni)
        if existentes:
            ids[tutor.clave] = existentes[0].id
            continue

        domicilio = None
        if tutor.calle and tutor.localidad:
            domicilio = DomicilioNuevo(
                calle=tutor.calle,
                localidad=tutor.localidad,
                piso=tutor.piso,
                departamento=tutor.departamento,
            )

        persona = padron_service.crear_persona(
            db,
            PersonaNueva(
                nombre=tutor.nombre,
                apellido=tutor.apellido,
                dni=tutor.dni,
                telefonos=[tutor.telefono] if tutor.telefono else [],
                domicilio=domicilio,
            ),
            # Sin teléfono solo se puede dar de alta como migrado.
            migrado=tutor.telefono is None,
        )
        ids[tutor.clave] = persona.id
        creados += 1
    return ids, creados


def _resolver_mascotas(
    db, tutores: dict[str, int]
) -> tuple[dict[str, int], int, int]:
    especies = {
        especie.nombre.casefold(): especie.id
        for especie in padron_service.listar_especies(db)
    }
    tamanios = {
        tamanio.nombre.casefold(): tamanio.id
        for tamanio in padron_service.listar_tamanios(db)
    }

    ids: dict[str, int] = {}
    creados = 0
    actualizados = 0
    for mascota in MASCOTAS:
        persona_id = tutores[mascota.tutor]
        especie_id = especies.get(mascota.especie.casefold())
        if especie_id is None:
            raise SeedError(f"Falta la especie '{mascota.especie}' en el catálogo.")

        raza_id = None
        if mascota.raza:
            raza_id = padron_service.crear_raza(
                db, RazaNueva(nombre=mascota.raza, especie_id=especie_id)
            ).id

        tamanio_id = (
            tamanios.get(mascota.tamanio.casefold()) if mascota.tamanio else None
        )
        peso = Decimal(mascota.peso_kg) if mascota.peso_kg else None
        nacimiento = _fecha_nacimiento_aprox(mascota.edad_meses)

        existente = next(
            (
                paciente
                for paciente in padron_service.pacientes_de_persona(db, persona_id)
                if paciente.nombre.strip().casefold() == mascota.nombre.strip().casefold()
            ),
            None,
        )
        if existente is not None:
            detalle = padron_service.obtener_paciente(db, existente.id)
            if detalle is None:
                raise SeedError(f"No se pudo leer la mascota '{mascota.nombre}'.")
            cambios: dict[str, object] = {}
            if detalle.raza_id is None and raza_id is not None:
                cambios["raza_id"] = raza_id
            if detalle.tamanio_id is None and tamanio_id is not None:
                cambios["tamanio_id"] = tamanio_id
            if detalle.peso_kg is None and peso is not None:
                cambios["peso_kg"] = peso
            if detalle.fecha_nacimiento_aprox is None and nacimiento is not None:
                cambios["fecha_nacimiento_aprox"] = nacimiento
            if cambios:
                padron_service.actualizar_paciente(
                    db, existente.id, PacienteActualizar(**cambios)
                )
                actualizados += 1
            ids[mascota.clave] = existente.id
            continue

        paciente = padron_service.crear_paciente(
            db,
            PacienteNuevo(
                nombre=mascota.nombre,
                especie_id=especie_id,
                raza_id=raza_id,
                tamanio_id=tamanio_id,
                peso_kg=peso,
                fecha_nacimiento_aprox=nacimiento,
                titular_persona_id=persona_id,
            ),
        )
        ids[mascota.clave] = paciente.id
        creados += 1
    return ids, creados, actualizados


def _coincide(cargo, demo: CargoDemo) -> bool:
    return (
        cargo.referencia_tipo == REFERENCIA_SEED
        and cargo.referencia_id == demo.numero
    ) or cargo.concepto == demo.concepto


def _resolver_cargos(
    db, tutores: dict[str, int], mascotas: dict[str, int], usuario_id: int
) -> tuple[int, int, int, int]:
    mascotas_por_clave = {mascota.clave: mascota for mascota in MASCOTAS}
    cargos_creados = 0
    cargos_existentes = 0
    pagos_creados = 0
    ajustes_creados = 0

    for demo in CARGOS:
        mascota = mascotas_por_clave[demo.mascota]
        persona_id = tutores[mascota.tutor]
        paciente_id = mascotas[demo.mascota]

        cuenta = cobros_service.cuenta_persona(db, persona_id)
        encontrado = next(
            (item for item in cuenta.cargos if _coincide(item.cargo, demo)),
            None,
        )
        if encontrado is None:
            cargo = cobros_service.crear_cargo(
                db,
                persona_id=persona_id,
                paciente_id=paciente_id,
                concepto=demo.concepto,
                total_centavos=demo.total_centavos,
                referencia_tipo=REFERENCIA_SEED,
                referencia_id=demo.numero,
                usuario_id=usuario_id,
            )
            cargo_id = cargo.id
            pagos_existentes: list[object] = []
            cargos_creados += 1
            estado = "creado"
        else:
            cargo_id = encontrado.cargo.id
            pagos_existentes = encontrado.pagos
            cargos_existentes += 1
            estado = "existente"

        if demo.ajuste is not None:
            ajustes = cobros_service.listar_ajustes(db, cargo_id)
            if not ajustes:
                cobros_service.ajustar_precio(
                    db,
                    cargo_id=cargo_id,
                    nuevo_total_centavos=demo.ajuste.nuevo_total_centavos,
                    motivo=demo.ajuste.motivo,
                    usuario_id=usuario_id,
                    rol=Rol.DUENIO,
                )
                ajustes_creados += 1

        claves = {
            pago.clave_idempotencia
            for pago in pagos_existentes
            if pago.clave_idempotencia
        }
        for indice, pago in enumerate(demo.pagos):
            clave = f"{REFERENCIA_SEED}:{demo.numero}:{indice}"
            if clave in claves:
                continue
            cobros_service.registrar_pago(
                db,
                cargo_id=cargo_id,
                monto_centavos=pago.monto_centavos,
                medio=pago.medio,
                es_sena=pago.es_sena,
                usuario_id=usuario_id,
                fecha_pago=demo.fecha,
                clave_idempotencia=clave,
            )
            pagos_creados += 1

        detalle = cobros_service.obtener_cargo_detalle(db, cargo_id)
        print(
            f"  {demo.referencia} {mascota.nombre}: {demo.concepto} -> {estado} · "
            f"total {dinero.formatear_pesos(int(detalle.total_vigente))} · "
            f"saldo {dinero.formatear_pesos(int(detalle.saldo))} · "
            f"{len(demo.pagos)} pago(s) en el dato"
        )

    return cargos_creados, cargos_existentes, pagos_creados, ajustes_creados


def main() -> int:
    with SessionLocal() as db:
        try:
            usuario = _elegir_usuario(db)
            padron_seed.sembrar_especies_tamanios_tipo_contacto(db)
            cobros_seed.sembrar_medios_pago(db)

            print(f"Usuario que registra: {usuario.username} ({usuario.rol.value})")
            tutores, tutores_creados = _resolver_tutores(db)
            mascotas, mascotas_creadas, mascotas_actualizadas = _resolver_mascotas(
                db, tutores
            )
            cargos_creados, cargos_existentes, pagos_creados, ajustes_creados = (
                _resolver_cargos(db, tutores, mascotas, usuario.id)
            )

            deudores = cobros_service.listar_deudores(
                db,
                orden="monto",
                solo_migracion=False,
                limite=100,
                desplazamiento=0,
            )
            total = sum(deudor.saldo_total_centavos for deudor in deudores)

            print()
            print("Resumen:")
            print(
                f"  Tutores: {tutores_creados} creados, "
                f"{len(TUTORES) - tutores_creados} existentes"
            )
            print(
                f"  Mascotas: {mascotas_creadas} creadas, "
                f"{len(MASCOTAS) - mascotas_creadas} existentes "
                f"({mascotas_actualizadas} completadas)"
            )
            print(
                f"  Cargos: {cargos_creados} creados, {cargos_existentes} existentes"
            )
            print(f"  Pagos nuevos: {pagos_creados}")
            print(f"  Ajustes de precio nuevos: {ajustes_creados}")
            print(f"  Deudores: {len(deudores)} · cartera {dinero.formatear_pesos(total)}")
            for deudor in deudores:
                print(
                    f"    {deudor.persona.apellido}, {deudor.persona.nombre}: "
                    f"{dinero.formatear_pesos(deudor.saldo_total_centavos)}"
                )

            print()
            print(
                "No persistido (sin módulo): detalle clínico y veterinario, "
                "cuidados de estadía y fechas de ingreso/egreso como entidad."
            )
        except SeedError as exc:
            print(f"No se pudo sembrar: {exc}", file=sys.stderr)
            return 1
        except (
            padron_service.DatosInvalidos,
            padron_service.DniDuplicado,
            padron_service.PosibleDuplicado,
            cobros_service.CobrosError,
        ) as exc:
            db.rollback()
            print(f"No se pudo sembrar: {exc}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
