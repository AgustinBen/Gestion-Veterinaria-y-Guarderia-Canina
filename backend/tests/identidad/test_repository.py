"""Tests del repositorio de identidad."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.identidad import repository
from app.modules.identidad.models import Usuario
from app.modules.identidad.permisos import Rol


def _crear(
    db: Session,
    *,
    username: str,
    rol: Rol = Rol.PERSONAL,
    activo: bool = True,
    empleado_id: int | None = None,
) -> Usuario:
    usuario = repository.crear_usuario(
        db,
        username=username,
        password_hash="$argon2id$hash-de-prueba",
        rol=rol,
        empleado_id=empleado_id,
    )
    usuario.activo = activo
    db.commit()
    db.refresh(usuario)
    return usuario


def test_crear_y_obtener_por_id_y_username(db_session: Session) -> None:
    creado = _crear(db_session, username="ana", rol=Rol.DUENIO)

    por_id = repository.obtener_por_id(db_session, creado.id)
    por_username = repository.obtener_por_username(db_session, "ana")

    assert por_id is not None
    assert por_username is not None
    assert por_id.id == creado.id
    assert por_username.username == "ana"
    assert por_username.rol is Rol.DUENIO
    assert por_username.activo is True
    assert por_username.creado_en is not None


def test_obtener_inexistentes_devuelve_none(db_session: Session) -> None:
    assert repository.obtener_por_id(db_session, 999) is None
    assert repository.obtener_por_username(db_session, "nadie") is None


def test_listar_ordenado_por_id(db_session: Session) -> None:
    _crear(db_session, username="carla")
    _crear(db_session, username="ana")
    _crear(db_session, username="beto")

    usuarios = repository.listar_usuarios(db_session)

    assert [usuario.username for usuario in usuarios] == ["carla", "ana", "beto"]
    assert [usuario.id for usuario in usuarios] == sorted(usuario.id for usuario in usuarios)


def test_username_es_unico(db_session: Session) -> None:
    _crear(db_session, username="ana")

    with pytest.raises(IntegrityError):
        _crear(db_session, username="ana")

    db_session.rollback()
    assert len(repository.listar_usuarios(db_session)) == 1


def test_empleado_id_no_tiene_foreign_key(db_session: Session) -> None:
    # En T-10 un entero cualquiera debe poder guardarse.
    usuario = _crear(db_session, username="veterinaria", empleado_id=999_999)

    assert usuario.empleado_id == 999_999


def test_rol_se_guarda_como_texto(db_session: Session) -> None:
    _crear(db_session, username="duenia", rol=Rol.DUENIO)

    rol_crudo = db_session.execute(text("SELECT rol FROM usuario")).scalar_one()

    assert rol_crudo == "DUENIO"


def test_contar_duenios_activos(db_session: Session) -> None:
    activo_1 = _crear(db_session, username="duenio1", rol=Rol.DUENIO)
    _crear(db_session, username="duenio2", rol=Rol.DUENIO)
    _crear(db_session, username="duenio_inactivo", rol=Rol.DUENIO, activo=False)
    _crear(db_session, username="personal", rol=Rol.PERSONAL)

    assert repository.contar_duenios_activos(db_session) == 2
    assert repository.contar_duenios_activos(db_session, excluir_id=activo_1.id) == 1


def test_listar_y_obtener_configuracion(db_session: Session, sembrar_config) -> None:
    sembrar_config("modulo_b", 42, "int", modulo="guarderia")
    sembrar_config("modulo_a", "texto", "str", modulo="identidad")

    claves = [param.clave for param in repository.listar_configuracion(db_session)]
    encontrado = repository.obtener_configuracion(db_session, "modulo_b")

    assert claves == ["modulo_a", "modulo_b"]
    assert encontrado is not None
    assert encontrado.tipo == "int"
    assert repository.obtener_configuracion(db_session, "no_existe") is None
