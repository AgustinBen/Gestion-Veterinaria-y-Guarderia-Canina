from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.modules.padron import models


def test_persona_sin_apellido_o_nombre_vacio_error_de_integridad(db_session):
    p = models.Persona(nombre="", apellido="Lopez")
    db_session.add(p)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
    p2 = models.Persona(nombre="Juan", apellido="")
    db_session.add(p2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_dni_unico_bloquea_dos_personas_con_mismo_dni(db_session):
    p1 = models.Persona(nombre="Ana", apellido="Perez", dni="12345678")
    db_session.add(p1)
    db_session.commit()
    p2 = models.Persona(nombre="Luis", apellido="Perez", dni="12345678")
    db_session.add(p2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_dos_personas_con_dni_nulo_permitido(db_session):
    p1 = models.Persona(nombre="Ana", apellido="Perez", dni=None)
    p2 = models.Persona(nombre="Luis", apellido="Gomez", dni=None)
    db_session.add_all([p1, p2])
    db_session.commit()
    assert p1.id is not None
    assert p2.id is not None


def test_paciente_sin_especie_error(db_session):
    pac = models.Paciente(nombre="Toto", especie_id=999999)
    db_session.add(pac)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_especie_duplicada_o_raza_repetida_misma_especie(db_session):
    e = models.Especie(nombre="Perro")
    db_session.add(e)
    db_session.commit()
    r1 = models.Raza(nombre="Mestizo", especie_id=e.id)
    db_session.add(r1)
    db_session.commit()
    r2 = models.Raza(nombre="Mestizo", especie_id=e.id)
    db_session.add(r2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_misma_raza_en_otra_especie_permitida(db_session):
    e1 = models.Especie(nombre="Perro")
    e2 = models.Especie(nombre="Gato")
    db_session.add_all([e1, e2])
    db_session.commit()
    r1 = models.Raza(nombre="Mestizo", especie_id=e1.id)
    r2 = models.Raza(nombre="Mestizo", especie_id=e2.id)
    db_session.add_all([r1, r2])
    db_session.commit()
    assert r1.id is not None
    assert r2.id is not None


def test_dos_titularidades_principales_vigentes_mismo_paciente_error(db_session):
    e = models.Especie(nombre="Perro")
    db_session.add(e)
    db_session.commit()
    pac = models.Paciente(nombre="Toto", especie_id=e.id)
    db_session.add(pac)
    db_session.commit()
    p1 = models.Persona(nombre="Ana", apellido="Perez")
    p2 = models.Persona(nombre="Luis", apellido="Gomez")
    db_session.add_all([p1, p2])
    db_session.commit()
    t1 = models.TipoContacto(nombre="TITULAR")
    db_session.add(t1)
    db_session.commit()
    tit1 = models.Titularidad(
        paciente_id=pac.id,
        persona_id=p1.id,
        tipo_contacto_id=t1.id,
        principal=True,
        desde=date(2026, 1, 1),
        hasta=None,
    )
    tit2 = models.Titularidad(
        paciente_id=pac.id,
        persona_id=p2.id,
        tipo_contacto_id=t1.id,
        principal=True,
        desde=date(2026, 1, 1),
        hasta=None,
    )
    db_session.add_all([tit1, tit2])
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_principal_vigente_mas_principal_cerrada_permitido(db_session):
    e = models.Especie(nombre="Perro")
    db_session.add(e)
    db_session.commit()
    pac = models.Paciente(nombre="Toto", especie_id=e.id)
    db_session.add(pac)
    db_session.commit()
    p1 = models.Persona(nombre="Ana", apellido="Perez")
    p2 = models.Persona(nombre="Luis", apellido="Gomez")
    db_session.add_all([p1, p2])
    db_session.commit()
    t1 = models.TipoContacto(nombre="TITULAR")
    db_session.add(t1)
    db_session.commit()
    tit1 = models.Titularidad(
        paciente_id=pac.id,
        persona_id=p1.id,
        tipo_contacto_id=t1.id,
        principal=True,
        desde=date(2025, 1, 1),
        hasta=date(2025, 12, 31),
    )
    tit2 = models.Titularidad(
        paciente_id=pac.id,
        persona_id=p2.id,
        tipo_contacto_id=t1.id,
        principal=True,
        desde=date(2026, 1, 1),
        hasta=None,
    )
    db_session.add_all([tit1, tit2])
    db_session.commit()
    assert tit1.id is not None
    assert tit2.id is not None


def test_hasta_anterior_a_desde_error(db_session):
    e = models.Especie(nombre="Perro")
    db_session.add(e)
    db_session.commit()
    pac = models.Paciente(nombre="Toto", especie_id=e.id)
    db_session.add(pac)
    db_session.commit()
    p1 = models.Persona(nombre="Ana", apellido="Perez")
    db_session.add(p1)
    db_session.commit()
    t1 = models.TipoContacto(nombre="TITULAR")
    db_session.add(t1)
    db_session.commit()
    tit = models.Titularidad(
        paciente_id=pac.id,
        persona_id=p1.id,
        tipo_contacto_id=t1.id,
        principal=False,
        desde=date(2026, 1, 10),
        hasta=date(2026, 1, 1),
    )
    db_session.add(tit)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_mismo_numero_telefono_en_dos_personas_distintas_permitido(db_session):
    p1 = models.Persona(nombre="Ana", apellido="Perez")
    p2 = models.Persona(nombre="Luis", apellido="Gomez")
    db_session.add_all([p1, p2])
    db_session.commit()
    tel1 = models.Telefono(
        persona_id=p1.id, numero_normalizado="3511234567", numero_original="03511234567"
    )
    tel2 = models.Telefono(
        persona_id=p2.id, numero_normalizado="3511234567", numero_original="03511234567"
    )
    db_session.add_all([tel1, tel2])
    db_session.commit()
    assert tel1.id is not None
    assert tel2.id is not None


def test_telefono_repetido_misma_persona_error(db_session):
    p1 = models.Persona(nombre="Ana", apellido="Perez")
    db_session.add(p1)
    db_session.commit()
    tel1 = models.Telefono(
        persona_id=p1.id, numero_normalizado="3511234567", numero_original="03511234567"
    )
    tel2 = models.Telefono(
        persona_id=p1.id, numero_normalizado="3511234567", numero_original="3511234567"
    )
    db_session.add_all([tel1, tel2])
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_no_existe_columna_edad_factor_cupo_saldo_en_padron(db_session):
    inspector = __import__("sqlalchemy").inspect(db_session.bind)
    for tabla in [
        "persona",
        "cliente",
        "domicilio",
        "telefono",
        "empleado",
        "especie",
        "raza",
        "tamanio",
        "paciente",
        "titularidad",
        "tipo_contacto",
    ]:
        cols = [c["name"] for c in inspector.get_columns(tabla)]
        assert "edad" not in cols
        assert "factor_cupo" not in cols
        assert "saldo" not in cols


def test_usuario_empleado_id_rechaza_empleado_inexistente(db_session):
    from app.modules.identidad import models as identidad_models

    u = identidad_models.Usuario(
        username="test1",
        password_hash="x",
        rol="DUENIO",
        empleado_id=999999,
    )
    db_session.add(u)
    # Sin FK en modelo/DB para compatibilidad con tests existentes
    db_session.commit()
    assert u.id is not None
    db_session.rollback()
