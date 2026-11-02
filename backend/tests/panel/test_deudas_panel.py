"""Deudas del panel, separadas de la rentabilidad (RN-40, T-46)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.cobros import service as cobros_service
from app.modules.cobros.schemas import OrigenCargo, TipoServicio
from tests.panel.conftest import EscenarioPanel


def _deudas(client: TestClient, headers: dict[str, str]) -> dict:
    respuesta = client.get("/api/panel/deudas", headers=headers)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _resumen(client: TestClient, headers: dict[str, str], panel_escenario: EscenarioPanel) -> dict:
    respuesta = client.get(
        "/api/panel/resumen",
        params={
            "desde": panel_escenario.desde.isoformat(),
            "hasta": panel_escenario.hasta.isoformat(),
        },
        headers=headers,
    )
    assert respuesta.status_code == 200
    return respuesta.json()


def test_deudas_totales_y_mayores_deudores(
    client: TestClient, tokens: dict[str, dict[str, str]], panel_escenario: EscenarioPanel
) -> None:
    datos = _deudas(client, tokens["duenio"])

    assert datos["total_adeudado_centavos"] == 7_000
    assert datos["cantidad_clientes"] == 1
    assert datos["deuda_migracion_centavos"] == 0
    assert len(datos["mayores_deudores"]) == 1
    deudor = datos["mayores_deudores"][0]
    assert deudor["persona_id"] == panel_escenario.persona_deudora_id
    assert deudor["nombre"] == "Cliente"
    assert deudor["apellido"] == "Deudor"
    assert deudor["saldo_total_centavos"] == 7_000
    assert deudor["migracion_centavos"] == 0
    assert deudor["cantidad_cargos_pendientes"] == 1


def test_deuda_migrada_aparece_aparte(
    client: TestClient,
    db_session: Session,
    tokens: dict[str, dict[str, str]],
    panel_escenario: EscenarioPanel,
) -> None:
    cobros_service.crear_cargo(
        db_session,
        persona_id=panel_escenario.persona_deudora_id,
        concepto="Deuda histórica",
        total_centavos=3_000,
        tipo_servicio=TipoServicio.MIGRACION,
        origen=OrigenCargo.MIGRACION,
        usuario_id=panel_escenario.usuario_id,
    )

    datos = _deudas(client, tokens["duenio"])
    assert datos["total_adeudado_centavos"] == 10_000
    assert datos["deuda_migracion_centavos"] == 3_000
    assert datos["cantidad_clientes"] == 1


def test_deudas_no_se_restan_de_la_rentabilidad(
    client: TestClient,
    db_session: Session,
    tokens: dict[str, dict[str, str]],
    panel_escenario: EscenarioPanel,
) -> None:
    antes = _resumen(client, tokens["duenio"], panel_escenario)
    cobros_service.crear_cargo(
        db_session,
        persona_id=panel_escenario.persona_deudora_id,
        concepto="Nueva deuda",
        total_centavos=1_000,
        tipo_servicio=TipoServicio.CONSULTA,
        usuario_id=panel_escenario.usuario_id,
    )
    despues = _resumen(client, tokens["duenio"], panel_escenario)

    assert antes["rentabilidad_neta_centavos"] == 27_000
    assert despues["rentabilidad_neta_centavos"] == 27_000
