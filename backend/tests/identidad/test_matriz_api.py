"""Tests de la matriz de permisos aplicada a endpoints de prueba."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.identidad.deps import require_acceso
from app.modules.identidad.permisos import Nivel, Recurso, Rol

# Matriz esperada escrita a mano: (lectura, escritura) -> status HTTP.
MATRIZ_ESPERADA: dict[tuple[Recurso, Rol], tuple[int, int]] = {
    (Recurso.USUARIOS_CONFIG, Rol.DUENIO): (200, 200),
    (Recurso.USUARIOS_CONFIG, Rol.PERSONAL): (403, 403),
    (Recurso.USUARIOS_CONFIG, Rol.VETERINARIO): (403, 403),
    (Recurso.FINANZAS, Rol.DUENIO): (200, 200),
    (Recurso.FINANZAS, Rol.PERSONAL): (403, 403),
    (Recurso.FINANZAS, Rol.VETERINARIO): (403, 403),
    (Recurso.DEUDAS_COBROS, Rol.DUENIO): (200, 200),
    (Recurso.DEUDAS_COBROS, Rol.PERSONAL): (200, 200),
    (Recurso.DEUDAS_COBROS, Rol.VETERINARIO): (403, 403),
    (Recurso.PADRON, Rol.DUENIO): (200, 200),
    (Recurso.PADRON, Rol.PERSONAL): (200, 200),
    (Recurso.PADRON, Rol.VETERINARIO): (200, 403),
    (Recurso.RESERVAS_CUPO, Rol.DUENIO): (200, 200),
    (Recurso.RESERVAS_CUPO, Rol.PERSONAL): (200, 200),
    (Recurso.RESERVAS_CUPO, Rol.VETERINARIO): (200, 403),
    (Recurso.EMERGENCIA, Rol.DUENIO): (200, 200),
    (Recurso.EMERGENCIA, Rol.PERSONAL): (403, 403),
    (Recurso.EMERGENCIA, Rol.VETERINARIO): (403, 403),
    (Recurso.TURNOS, Rol.DUENIO): (200, 200),
    (Recurso.TURNOS, Rol.PERSONAL): (200, 200),
    (Recurso.TURNOS, Rol.VETERINARIO): (200, 200),
    (Recurso.HISTORIA_CLINICA, Rol.DUENIO): (200, 200),
    (Recurso.HISTORIA_CLINICA, Rol.PERSONAL): (200, 403),
    (Recurso.HISTORIA_CLINICA, Rol.VETERINARIO): (200, 200),
}

NIVELES = (Nivel.LECTURA, Nivel.ESCRITURA)
INDICE_NIVEL = {Nivel.LECTURA: 0, Nivel.ESCRITURA: 1}
METODO_NIVEL = {Nivel.LECTURA: "GET", Nivel.ESCRITURA: "POST"}

RUTAS = [
    (METODO_NIVEL[nivel], f"/{recurso.value}/{nivel.name.lower()}")
    for recurso in Recurso
    for nivel in NIVELES
]
CASOS_MATRIZ = [
    (recurso, rol, nivel)
    for recurso in Recurso
    for rol in Rol
    for nivel in NIVELES
]


def _crear_endpoint(
    recurso: Recurso, nivel: Nivel
) -> Callable[[], dict[str, str]]:
    def _endpoint() -> dict[str, str]:
        return {"recurso": recurso.value, "nivel": nivel.name}

    return _endpoint


def _crear_app_matriz() -> FastAPI:
    """Arma un router de prueba con lectura y escritura por cada recurso."""
    app = FastAPI()
    router = APIRouter()

    for recurso in Recurso:
        for nivel in NIVELES:
            router.add_api_route(
                f"/{recurso.value}/{nivel.name.lower()}",
                _crear_endpoint(recurso, nivel),
                methods=[METODO_NIVEL[nivel]],
                dependencies=[Depends(require_acceso(recurso, nivel))],
            )

    app.include_router(router)
    return app


@pytest.fixture
def client_matriz(db_session: Session):
    app = _crear_app_matriz()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_cobertura_de_matriz_y_rutas() -> None:
    assert len(RUTAS) == 16
    assert len(CASOS_MATRIZ) == 48
    assert set(MATRIZ_ESPERADA) == {
        (recurso, rol) for recurso in Recurso for rol in Rol
    }


@pytest.mark.parametrize(("recurso", "rol", "nivel"), CASOS_MATRIZ)
def test_matriz_api(
    client_matriz: TestClient,
    crear_usuario,
    token_de,
    recurso: Recurso,
    rol: Rol,
    nivel: Nivel,
) -> None:
    usuario = crear_usuario(f"user_{rol.value}", rol=rol)
    esperado = MATRIZ_ESPERADA[(recurso, rol)][INDICE_NIVEL[nivel]]

    respuesta = client_matriz.request(
        METODO_NIVEL[nivel],
        f"/{recurso.value}/{nivel.name.lower()}",
        headers=_auth(token_de(usuario)),
    )

    assert respuesta.status_code == esperado


@pytest.mark.parametrize(("metodo", "ruta"), RUTAS)
def test_rutas_sin_token_401(
    client_matriz: TestClient, metodo: str, ruta: str
) -> None:
    respuesta = client_matriz.request(metodo, ruta)

    assert respuesta.status_code == 401
    assert respuesta.json() == {"detail": "No autenticado"}
    assert respuesta.headers["WWW-Authenticate"] == "Bearer"
