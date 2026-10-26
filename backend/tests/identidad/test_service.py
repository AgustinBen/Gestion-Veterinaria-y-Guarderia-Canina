"""Tests del bootstrap del Dueño y de la validación de contraseñas."""

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.identidad import security, service
from app.modules.identidad.models import Usuario
from app.modules.identidad.permisos import Rol
from app.modules.identidad.schemas import UsuarioCrear


def _contar_usuarios(db: Session) -> int:
    return db.execute(select(func.count()).select_from(Usuario)).scalar_one()


def test_crear_dueno_inicial_es_idempotente(
    db_session: Session, password_prueba
) -> None:
    usuario, creado = service.crear_dueno_inicial(
        db_session, "  Duenio  ", password_prueba
    )

    assert creado is True
    assert usuario.username == "duenio"
    assert usuario.rol == Rol.DUENIO
    assert usuario.activo is True
    assert usuario.empleado_id is None
    assert security.verificar_password(usuario.password_hash, password_prueba)

    hash_inicial = usuario.password_hash
    usuario2, creado2 = service.crear_dueno_inicial(
        db_session, "DUENIO", "otra-clave-distinta"
    )

    assert creado2 is False
    assert usuario2.id == usuario.id
    assert usuario2.password_hash == hash_inicial
    assert security.verificar_password(usuario2.password_hash, password_prueba)
    assert not security.verificar_password(
        usuario2.password_hash, "otra-clave-distinta"
    )
    assert _contar_usuarios(db_session) == 1


def test_crear_dueno_inicial_rechaza_username_de_otro_rol(
    db_session: Session, crear_usuario, password_prueba
) -> None:
    existente = crear_usuario("personal", rol=Rol.PERSONAL)
    antes = _contar_usuarios(db_session)

    with pytest.raises(service.UsuarioExistenteNoDuenio):
        service.crear_dueno_inicial(db_session, "PERSONAL", password_prueba)

    assert _contar_usuarios(db_session) == antes
    assert existente.rol == Rol.PERSONAL


def test_crear_dueno_inicial_exige_password_minima(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    minimo = get_settings().password_min_length + 4
    monkeypatch.setattr(get_settings(), "password_min_length", minimo)

    with pytest.raises(service.DatosInvalidos):
        service.crear_dueno_inicial(
            db_session, "duenio", "x" * (minimo - 1)
        )

    assert _contar_usuarios(db_session) == 0


def test_crear_usuario_password_minima_configurable(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    minimo = get_settings().password_min_length + 4
    monkeypatch.setattr(get_settings(), "password_min_length", minimo)

    with pytest.raises(service.DatosInvalidos):
        service.crear_usuario(
            db_session,
            UsuarioCrear(
                username="corta",
                password="x" * (minimo - 1),
                rol=Rol.PERSONAL,
            ),
        )

    assert _contar_usuarios(db_session) == 0

    creado = service.crear_usuario(
        db_session,
        UsuarioCrear(
            username="en_minimo",
            password="x" * minimo,
            rol=Rol.PERSONAL,
        ),
    )

    assert creado.username == "en_minimo"
    assert _contar_usuarios(db_session) == 1
