"""Detalle de servicios por cliente, solo para el Dueño (T-46)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.padron import service as padron_service
from app.modules.padron.schemas import PersonaNueva
from tests.panel.conftest import EscenarioPanel


def test_detalle_lista_cargos_con_tipo_pagado_y_saldo(
    client: TestClient, tokens: dict[str, dict[str, str]], panel_escenario: EscenarioPanel
) -> None:
    respuesta = client.get(
        f"/api/panel/clientes/{panel_escenario.persona_id}/servicios",
        headers=tokens["duenio"],
    )
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()

    assert datos["persona_id"] == panel_escenario.persona_id
    assert len(datos["servicios"]) == 2
    servicio = next(
        item
        for item in datos["servicios"]
        if item["cargo_id"] == panel_escenario.cargo_guarderia_id
    )
    assert servicio["tipo_servicio"] == "GUARDERIA"
    assert servicio["total_centavos"] == 28_000
    assert servicio["pagado_centavos"] == 28_000
    assert servicio["saldo_centavos"] == 0
    assert servicio["ajustes"] == 1


def test_cliente_sin_cargos_devuelve_lista_vacia(
    client: TestClient,
    db_session: Session,
    tokens: dict[str, dict[str, str]],
    panel_escenario: EscenarioPanel,
) -> None:
    persona = padron_service.crear_persona(
        db_session, PersonaNueva(nombre="Sin", apellido="Cargos"), migrado=True
    )
    respuesta = client.get(
        f"/api/panel/clientes/{persona.id}/servicios", headers=tokens["duenio"]
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["servicios"] == []


def test_cliente_inexistente_404(
    client: TestClient, tokens: dict[str, dict[str, str]], panel_escenario: EscenarioPanel
) -> None:
    respuesta = client.get(
        "/api/panel/clientes/999999/servicios", headers=tokens["duenio"]
    )
    assert respuesta.status_code == 404
