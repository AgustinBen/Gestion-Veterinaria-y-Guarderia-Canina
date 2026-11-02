"""Ingresos agrupados por servicio y por medio (T-46)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.panel.conftest import EscenarioPanel


def _get(
    client: TestClient,
    headers: dict[str, str],
    panel_escenario: EscenarioPanel,
    ruta: str,
) -> list[dict]:
    respuesta = client.get(
        ruta,
        params={
            "desde": panel_escenario.desde.isoformat(),
            "hasta": panel_escenario.hasta.isoformat(),
        },
        headers=headers,
    )
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def test_ingresos_por_servicio(
    client: TestClient, tokens: dict[str, dict[str, str]], panel_escenario: EscenarioPanel
) -> None:
    filas = _get(client, tokens["duenio"], panel_escenario, "/api/panel/ingresos-por-servicio")
    por_tipo = {fila["tipo_servicio"]: fila["ingresos_centavos"] for fila in filas}

    assert por_tipo["GUARDERIA"] == 28_000
    assert por_tipo["CONSULTA"] == 12_000


def test_ingresos_por_medio(
    client: TestClient, tokens: dict[str, dict[str, str]], panel_escenario: EscenarioPanel
) -> None:
    filas = _get(client, tokens["duenio"], panel_escenario, "/api/panel/ingresos-por-medio")
    por_medio = {fila["medio"]: fila["ingresos_centavos"] for fila in filas}

    assert por_medio["EFECTIVO"] == 28_000
    assert por_medio["DEBITO"] == 12_000


def test_ingresos_por_servicio_filtrado_por_servicio(
    client: TestClient, tokens: dict[str, dict[str, str]], panel_escenario: EscenarioPanel
) -> None:
    respuesta = client.get(
        "/api/panel/ingresos-por-servicio",
        params={
            "desde": panel_escenario.desde.isoformat(),
            "hasta": panel_escenario.hasta.isoformat(),
            "servicio": "GUARDERIA",
        },
        headers=tokens["duenio"],
    )
    assert respuesta.status_code == 200
    assert respuesta.json() == [
        {"tipo_servicio": "GUARDERIA", "ingresos_centavos": 28_000}
    ]
