"""Historial de ingresos del panel financiero."""

from fastapi.testclient import TestClient

from tests.panel.conftest import EscenarioPanel


def test_historial_suma_igual_que_total_ingresos_y_orden_descendente(
    client: TestClient,
    tokens: dict[str, dict[str, str]],
    panel_escenario: EscenarioPanel,
) -> None:
    parametros = {
        "desde": panel_escenario.desde.isoformat(),
        "hasta": panel_escenario.hasta.isoformat(),
    }
    historial = client.get(
        "/api/panel/ingresos", params=parametros, headers=tokens["duenio"]
    )
    resumen = client.get(
        "/api/panel/resumen", params=parametros, headers=tokens["duenio"]
    )

    assert historial.status_code == 200, historial.text
    assert resumen.status_code == 200, resumen.text
    ingresos = historial.json()
    assert sum(item["monto_centavos"] for item in ingresos) == resumen.json()[
        "ingresos_centavos"
    ]
    assert ingresos[0]["estado"] == "Reverso"
    assert ingresos[0]["monto_centavos"] < 0
    assert [
        (item["fecha"], item["id"]) for item in ingresos
    ] == sorted(
        ((item["fecha"], item["id"]) for item in ingresos),
        reverse=True,
    )


def test_historial_aplica_filtros_y_limite(
    client: TestClient,
    tokens: dict[str, dict[str, str]],
    panel_escenario: EscenarioPanel,
) -> None:
    respuesta = client.get(
        "/api/panel/ingresos",
        params={
            "desde": panel_escenario.desde.isoformat(),
            "hasta": panel_escenario.hasta.isoformat(),
            "servicio": "GUARDERIA",
            "medio": "EFECTIVO",
            "limite": 1,
        },
        headers=tokens["duenio"],
    )

    assert respuesta.status_code == 200, respuesta.text
    assert len(respuesta.json()) == 1
    assert respuesta.json()[0]["tipo_servicio"] == "GUARDERIA"
    assert respuesta.json()[0]["medio"] == "EFECTIVO"
