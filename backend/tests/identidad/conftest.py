"""Fixtures compartidos de los tests del módulo identidad."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import app.modules.identidad.models  # noqa: F401
from app.core.config import get_settings
from app.modules.identidad import repository, security
from app.modules.identidad.models import Usuario
from app.modules.identidad.permisos import Rol

PASSWORD_PRUEBA = "clave-de-prueba-segura"


@pytest.fixture(autouse=True)
def _secret_key_de_pruebas(monkeypatch: pytest.MonkeyPatch) -> None:
    """Evita el warning de PyJWT por la clave default corta del proyecto."""
    monkeypatch.setattr(
        get_settings(),
        "secret_key",
        "clave-de-pruebas-de-identidad-con-mas-de-32-bytes",
    )


@pytest.fixture
def crear_usuario(db_session: Session):
    """Crea un usuario directo en la base, sin pasar por los endpoints."""

    def _crear(
        username: str,
        *,
        password: str = PASSWORD_PRUEBA,
        rol: Rol = Rol.PERSONAL,
        activo: bool = True,
        empleado_id: int | None = None,
    ) -> Usuario:
        usuario = repository.crear_usuario(
            db_session,
            username=username.strip().lower(),
            password_hash=security.hash_password(password),
            rol=rol,
            empleado_id=empleado_id,
        )
        usuario.activo = activo
        db_session.commit()
        db_session.refresh(usuario)
        return usuario

    return _crear


@pytest.fixture
def duenio(crear_usuario):
    return crear_usuario("duenio", rol=Rol.DUENIO)


@pytest.fixture
def token_de():
    """Genera un token para un usuario ya persistido."""

    def _token(usuario: Usuario, *, ahora: datetime | None = None) -> str:
        return security.crear_token(usuario.id, usuario.rol, ahora=ahora)

    return _token


@pytest.fixture
def password_prueba() -> str:
    return PASSWORD_PRUEBA


@pytest.fixture
def login(client: TestClient):
    """Llama al endpoint de login con la contraseña de prueba."""

    def _login(username: str, password: str = PASSWORD_PRUEBA):
        return client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
        )

    return _login


@pytest.fixture
def auth_de(client: TestClient):
    """Devuelve el header Authorization de un usuario activo."""

    def _auth(
        usuario: Usuario, password: str = PASSWORD_PRUEBA
    ) -> dict[str, str]:
        respuesta = client.post(
            "/api/auth/login",
            json={"username": usuario.username, "password": password},
        )
        assert respuesta.status_code == 200
        token = respuesta.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _auth
