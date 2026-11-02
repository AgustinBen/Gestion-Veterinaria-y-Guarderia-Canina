"""Serie diaria y mensual del panel (T-46)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.panel.conftest import EscenarioPanel


def _resumen(
    client: TestClient, headers: dict[str, str], panel_escenario: EscenarioPanel
) -> dict:
    respuesta = client.get(
        "/api/panel/resumen",
        params={
            "desde": panel_escenario.desde.isoformat(),
            "hasta": panel_escenario.hasta.isoformat(),
        },
        headers=headers,
    )
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _serie(
    client: TestClient,
    headers: dict[str, str],
    panel_escenario: EscenarioPanel,
    agrupar: str,
) -> dict:
    respuesta = client.get(
        "/api/panel/serie",
        params={
            "agrupar": agrupar,
            "desde": panel_escenario.desde.isoformat(),
            "hasta": panel_escenario.hasta.isoformat(),
        },
        headers=headers,
    )
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def test_serie_por_dia_suma_igual_al_resumen(
    client: TestClient, tokens: dict[str, dict[str, str]], panel_escenario: EscenarioPanel
) -> None:
    resumen = _resumen(client, tokens["duenio"], panel_escenario)
    serie = _serie(client, tokens["duenio"], panel_escenario, "dia")

    assert serie["agrupar"] == "dia"
    assert sum(p["ingresos_centavos"] for p in serie["puntos"]) == resumen[
        "ingresos_centavos"
    ]
    assert sum(p["egresos_operativos_centavos"] for p in serie["puntos"]) == resumen[
        "egresos_operativos_centavos"
    ]


def test_serie_por_mes_suma_igual_al_resumen(
    client: TestClient, tokens: dict[str, dict[str, str]], panel_escenario: EscenarioPanel
) -> None:
    resumen = _resumen(client, tokens["duenio"], panel_escenario)
    serie = _serie(client, tokens["duenio"], panel_escenario, "mes")

    assert serie["agrupar"] == "mes"
    assert sum(p["ingresos_centavos"] for p in serie["puntos"]) == resumen[
        "ingresos_centavos"
    ]
    assert sum(p["egresos_operativos_centavos"] for p in serie["puntos"]) == resumen[
        "egresos_operativos_centavos"
    ]


def test_agrupacion_invalida_422(
    client: TestClient, tokens: dict[str, dict[str, str]], panel_escenario: EscenarioPanel
) -> None:
    respuesta = client.get(
        "/api/panel/serie",
        params={
            "agrupar": "semana",
            "desde": panel_escenario.desde.isoformat(),
            "hasta": panel_escenario.hasta.isoformat(),
        },
        headers=tokens["duenio"],
    )
    assert respuesta.status_code == 422
