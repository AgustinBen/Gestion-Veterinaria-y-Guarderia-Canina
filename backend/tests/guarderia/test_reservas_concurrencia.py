from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from threading import Barrier

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.core.parametros import get_param
from app.modules.guarderia import service
from app.modules.guarderia.franjas import Franja
from app.modules.guarderia.models import Ocupacion, Reserva
from app.modules.guarderia.schemas import ReservaCrear
from app.modules.identidad.permisos import Rol


def test_dos_pedidos_simultaneos_no_superan_el_cupo(
    db_session,
    engine_sqlite,
    sembrar_cupo,
    crear_datos_reserva,
    crear_pacientes,
    crear_usuario,
    crear_ocupaciones,
) -> None:
    datos = crear_datos_reserva(cantidad_pacientes=2)
    usuario = crear_usuario(Rol.DUENIO)
    fecha = date.today() + timedelta(days=2)
    cupo_maximo = get_param(db_session, "guarderia.cupo_maximo")
    plazas_emergencia = get_param(db_session, "guarderia.plazas_emergencia")
    cupo_publico = cupo_maximo - plazas_emergencia
    pacientes_ocupados = crear_pacientes([("Perro", None)] * (cupo_publico - 1))
    for paciente_id in pacientes_ocupados:
        crear_ocupaciones(
            [paciente_id],
            fecha,
            Franja.DIA,
            usuario.id,
        )
    db_session.commit()

    sesiones = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine_sqlite,
        future=True,
    )
    barrera = Barrier(2)

    def enviar(paciente_id: int, clave: str) -> tuple[int, str]:
        solicitud = ReservaCrear(
            tutor_persona_id=datos.tutor_persona_id,
            paciente_ids=[paciente_id],
            desde_fecha=fecha,
            desde_franja=Franja.DIA,
            hasta_fecha=fecha,
            hasta_franja=Franja.DIA,
            cuidados_extras=[
                {"paciente_id": paciente_id, "cuidados_extras": False}
            ],
            total_centavos=300000,
        )
        barrera.wait()
        with sesiones() as db:
            try:
                service.crear_reserva(
                    db,
                    solicitud,
                    clave_idempotencia=clave,
                    usuario_id=usuario.id,
                )
            except service.ReservaCupoConflicto as exc:
                return 409, exc.resultado.codigo
        return 201, "CREADA"

    with ThreadPoolExecutor(max_workers=2) as pool:
        resultados = list(
            pool.map(
                lambda datos_envio: enviar(*datos_envio),
                [
                    (datos.paciente_ids[0], "concurrente-a"),
                    (datos.paciente_ids[1], "concurrente-b"),
                ],
            )
        )

    assert sorted(result[0] for result in resultados) == [201, 409]
    assert next(codigo for status, codigo in resultados if status == 409) == "SIN_CUPO"
    assert db_session.scalar(
        select(func.count(Reserva.id)).where(Reserva.clave_idempotencia.is_not(None))
    ) == 1
    assert db_session.scalar(
        select(func.count(Ocupacion.id)).where(
            Ocupacion.fecha == fecha,
            Ocupacion.franja == Franja.DIA,
        )
    ) == cupo_publico
