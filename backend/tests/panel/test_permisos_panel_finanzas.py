"""Permisos del panel: solo el Dueño accede a finanzas (RN-40, T-46)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.panel.conftest import EscenarioPanel


def _rutas(panel_escenario: EscenarioPanel) -> list[str]:
    return [
        "/api/panel/resumen",
        "/api/panel/serie",
        "/api/panel/ingresos-por-servicio",
        "/api/panel/ingresos-por-medio",
        "/api/panel/ingresos",
        "/api/panel/deudas",
        f"/api/panel/clientes/{panel_escenario.persona_id}/servicios",
    ]


def test_sin_token_401(
    client: TestClient, panel_escenario: EscenarioPanel
) -> None:
    for ruta in _rutas(panel_escenario):
        assert client.get(ruta).status_code == 401


def test_duenio_accede_a_todos_los_endpoints(
    client: TestClient, tokens: dict[str, dict[str, str]], panel_escenario: EscenarioPanel
) -> None:
    for ruta in _rutas(panel_escenario):
        assert client.get(ruta, headers=tokens["duenio"]).status_code == 200, ruta


@pytest.mark.parametrize("rol", ["personal", "veterinario"])
def test_personal_y_veterinario_403(
    client: TestClient,
    tokens: dict[str, dict[str, str]],
    panel_escenario: EscenarioPanel,
    rol: str,
) -> None:
    for ruta in _rutas(panel_escenario):
        assert client.get(ruta, headers=tokens[rol]).status_code == 403, ruta
