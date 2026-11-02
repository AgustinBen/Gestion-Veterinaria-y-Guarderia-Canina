from datetime import date, datetime, time, timedelta

from app.core import parametros
from app.modules.clinica.models import FranjaTurnoPersonal, TurnoPersonalDef
from app.modules.clinica.schemas import EmpleadoTraspaso
from app.modules.clinica.seed import sembrar_parametros
from app.modules.clinica.service import ventanas_traspaso_del_dia
from app.modules.clinica.traspaso import (
    TurnoDefinidoConPersonal,
    ventanas_traspaso,
)


def _definicion(dia: date) -> list[TurnoDefinidoConPersonal]:
    empleado = EmpleadoTraspaso(empleado_id=1, nombre="Veterinario")
    return [
        TurnoDefinidoConPersonal(
            fecha=dia,
            turno=FranjaTurnoPersonal.MANANA,
            hora_desde=time(6),
            hora_hasta=time(14),
            empleados=(empleado,),
        ),
        TurnoDefinidoConPersonal(
            fecha=dia,
            turno=FranjaTurnoPersonal.TARDE,
            hora_desde=time(14),
            hora_hasta=time(22),
            empleados=(empleado,),
        ),
        TurnoDefinidoConPersonal(
            fecha=dia,
            turno=FranjaTurnoPersonal.NOCHE,
            hora_desde=time(22),
            hora_hasta=time(6),
            empleados=(empleado,),
        ),
        TurnoDefinidoConPersonal(
            fecha=dia - timedelta(days=1),
            turno=FranjaTurnoPersonal.NOCHE,
            hora_desde=time(22),
            hora_hasta=time(6),
            empleados=(empleado,),
        ),
    ]


def test_ventanas_traspaso_incluye_cambio_nocturno_en_el_dia_que_ocurre() -> None:
    dia = date(2026, 11, 2)

    ventanas = ventanas_traspaso(dia, _definicion(dia), 30)

    assert [(item.inicio, item.fin) for item in ventanas] == [
        (datetime(2026, 11, 2, 13, 30), datetime(2026, 11, 2, 14)),
        (datetime(2026, 11, 2, 21, 30), datetime(2026, 11, 2, 22)),
        (datetime(2026, 11, 2, 5, 30), datetime(2026, 11, 2, 6)),
    ]
    assert ventanas[2].turno_sale == FranjaTurnoPersonal.NOCHE
    assert ventanas[2].turno_entra == FranjaTurnoPersonal.MANANA


def test_minutos_configurados_cambian_las_ventanas(db_session) -> None:
    sembrar_parametros(db_session)
    parametros.set_param(
        db_session,
        "clinica.minutos_traspaso",
        45,
        "int",
        modulo="clinica",
    )
    dia = date(2026, 11, 2)

    db_session.add_all(
        [
            TurnoPersonalDef(
                turno=FranjaTurnoPersonal.MANANA,
                hora_desde=time(6),
                hora_hasta=time(14),
            ),
            TurnoPersonalDef(
                turno=FranjaTurnoPersonal.TARDE,
                hora_desde=time(14),
                hora_hasta=time(22),
            ),
            TurnoPersonalDef(
                turno=FranjaTurnoPersonal.NOCHE,
                hora_desde=time(22),
                hora_hasta=time(6),
            ),
        ]
    )
    db_session.commit()
    ventanas = ventanas_traspaso_del_dia(db_session, dia)

    assert ventanas[0].inicio == datetime(2026, 11, 2, 13, 15)
