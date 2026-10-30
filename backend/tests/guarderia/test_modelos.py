from datetime import date

import pytest
from sqlalchemy import insert, inspect
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import Session

from app.core.base import Base
from app.modules.guarderia.franjas import Franja
from app.modules.guarderia.models import (
    EstadoReserva,
    HabilitacionEmergencia,
    Ocupacion,
    Reserva,
    ReservaPaciente,
)
from app.modules.guarderia.repository import contar_ocupacion


def _insertar(db_session: Session, tabla: str, **valores: object) -> int:
    resultado = db_session.execute(
        insert(Base.metadata.tables[tabla]).values(**valores)
    )
    return resultado.inserted_primary_key[0]


def _crear_referencias(db_session: Session) -> tuple[int, int, int]:
    tutor_id = _insertar(
        db_session,
        "persona",
        nombre="Tutor",
        apellido="Prueba",
    )
    especie_id = _insertar(db_session, "especie", nombre="Especie de prueba")
    paciente_id = _insertar(
        db_session,
        "paciente",
        nombre="Paciente de prueba",
        especie_id=especie_id,
    )
    usuario_id = _insertar(
        db_session,
        "usuario",
        username="usuario-prueba",
        password_hash="hash-prueba",
        rol="DUENIO",
    )
    return tutor_id, paciente_id, usuario_id


def _crear_reserva(
    db_session: Session,
    tutor_id: int,
    usuario_id: int,
    *,
    desde_fecha: date = date(2030, 1, 1),
    desde_franja: Franja = Franja.DIA,
    hasta_fecha: date = date(2030, 1, 1),
    hasta_franja: Franja = Franja.NOCHE,
    clave_idempotencia: str | None = None,
) -> Reserva:
    return Reserva(
        tutor_persona_id=tutor_id,
        desde_fecha=desde_fecha,
        desde_franja=desde_franja,
        hasta_fecha=hasta_fecha,
        hasta_franja=hasta_franja,
        estado=EstadoReserva.CONFIRMADA,
        clave_idempotencia=clave_idempotencia,
        creado_por=usuario_id,
    )


def test_franja_fuera_de_la_enumeracion_se_rechaza(db_session: Session) -> None:
    tutor_id, paciente_id, usuario_id = _crear_referencias(db_session)
    reserva = _crear_reserva(db_session, tutor_id, usuario_id)
    db_session.add(reserva)
    db_session.flush()

    db_session.add(
        Ocupacion(
            fecha=date(2030, 1, 1),
            franja="TARDE",
            reserva_id=reserva.id,
            paciente_id=paciente_id,
        )
    )
    with pytest.raises(StatementError):
        db_session.flush()


def test_reserva_con_fin_anterior_al_inicio_se_rechaza(db_session: Session) -> None:
    tutor_id, _, usuario_id = _crear_referencias(db_session)
    db_session.add(
        _crear_reserva(
            db_session,
            tutor_id,
            usuario_id,
            desde_franja=Franja.NOCHE,
            hasta_franja=Franja.DIA,
        )
    )

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_estado_fuera_de_la_lista_se_rechaza(db_session: Session) -> None:
    tutor_id, _, usuario_id = _crear_referencias(db_session)
    reserva = _crear_reserva(db_session, tutor_id, usuario_id)
    reserva.estado = "OTRO_ESTADO"
    db_session.add(reserva)

    with pytest.raises(StatementError):
        db_session.flush()


def test_ocupacion_unica_por_fecha_franja_y_paciente(db_session: Session) -> None:
    tutor_id, paciente_id, usuario_id = _crear_referencias(db_session)
    reserva = _crear_reserva(db_session, tutor_id, usuario_id)
    db_session.add(reserva)
    db_session.flush()
    ocupacion = Ocupacion(
        fecha=date(2030, 1, 1),
        franja=Franja.DIA,
        reserva_id=reserva.id,
        paciente_id=paciente_id,
    )
    db_session.add(ocupacion)
    db_session.commit()

    db_session.add(
        Ocupacion(
            fecha=date(2030, 1, 1),
            franja=Franja.DIA,
            reserva_id=reserva.id,
            paciente_id=paciente_id,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_mismo_paciente_puede_ocupar_dia_y_noche(db_session: Session) -> None:
    tutor_id, paciente_id, usuario_id = _crear_referencias(db_session)
    reserva = _crear_reserva(db_session, tutor_id, usuario_id)
    db_session.add(reserva)
    db_session.flush()
    db_session.add_all(
        [
            Ocupacion(
                fecha=date(2030, 1, 1),
                franja=Franja.DIA,
                reserva_id=reserva.id,
                paciente_id=paciente_id,
            ),
            Ocupacion(
                fecha=date(2030, 1, 1),
                franja=Franja.NOCHE,
                reserva_id=reserva.id,
                paciente_id=paciente_id,
            ),
        ]
    )
    db_session.commit()

    assert contar_ocupacion(db_session, date(2030, 1, 1), Franja.DIA) == 1
    assert contar_ocupacion(db_session, date(2030, 1, 1), Franja.NOCHE) == 1


def test_paciente_no_se_repite_en_una_reserva(db_session: Session) -> None:
    tutor_id, paciente_id, usuario_id = _crear_referencias(db_session)
    reserva = _crear_reserva(db_session, tutor_id, usuario_id)
    db_session.add(reserva)
    db_session.flush()
    db_session.add(
        ReservaPaciente(
            reserva_id=reserva.id,
            paciente_id=paciente_id,
            cuidados_extras=False,
        )
    )
    db_session.commit()

    db_session.add(
        ReservaPaciente(
            reserva_id=reserva.id,
            paciente_id=paciente_id,
            cuidados_extras=True,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


@pytest.mark.parametrize("motivo", ["", "  ", None])
def test_habilitacion_exige_motivo_no_vacio(db_session: Session, motivo: str | None) -> None:
    _, _, usuario_id = _crear_referencias(db_session)
    db_session.add(
        HabilitacionEmergencia(
            fecha=date(2030, 1, 1),
            franja=Franja.DIA,
            usuario_id=usuario_id,
            motivo=motivo,
        )
    )

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_clave_idempotencia_de_habilitacion_es_unica(db_session: Session) -> None:
    _, _, usuario_id = _crear_referencias(db_session)
    datos = {
        "fecha": date(2030, 1, 1),
        "franja": Franja.DIA,
        "usuario_id": usuario_id,
        "motivo": "Necesidad operativa",
        "clave_idempotencia": "solicitud-unica",
    }
    db_session.add(HabilitacionEmergencia(**datos))
    db_session.commit()

    db_session.add(HabilitacionEmergencia(**datos))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_reserva_puede_tener_clave_idempotencia_unica(db_session: Session) -> None:
    tutor_id, _, usuario_id = _crear_referencias(db_session)
    db_session.add(
        _crear_reserva(
            db_session,
            tutor_id,
            usuario_id,
            clave_idempotencia="solicitud-unica",
        )
    )
    db_session.commit()

    db_session.add(
        _crear_reserva(
            db_session,
            tutor_id,
            usuario_id,
            clave_idempotencia="solicitud-unica",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_tablas_de_ocupacion_no_tienen_columnas_de_unidades_o_tamanio(
    engine_sqlite,
) -> None:
    for tabla in ("ocupacion", "reserva_paciente"):
        columnas = {columna["name"] for columna in inspect(engine_sqlite).get_columns(tabla)}
        assert columnas.isdisjoint({"unidades", "factor", "tamanio"})


def test_consulta_de_ocupacion_filtra_por_fecha_y_franja(db_session: Session) -> None:
    tutor_id, paciente_id, usuario_id = _crear_referencias(db_session)
    reserva = _crear_reserva(db_session, tutor_id, usuario_id)
    db_session.add(reserva)
    db_session.flush()
    db_session.add(
        Ocupacion(
            fecha=date(2030, 1, 1),
            franja=Franja.NOCHE,
            reserva_id=reserva.id,
            paciente_id=paciente_id,
        )
    )
    db_session.commit()

    assert contar_ocupacion(db_session, date(2030, 1, 1), Franja.DIA) == 0
    assert contar_ocupacion(db_session, date(2030, 1, 1), Franja.NOCHE) == 1
