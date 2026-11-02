"""Resumen del panel: ingresos, egresos, gastos y rentabilidad (T-46)."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.cobros import service as cobros_service
from app.modules.cobros.schemas import OrigenCargo, TipoServicio
from tests.panel.conftest import EscenarioPanel


def _resumen(client: TestClient, headers: dict[str, str], **params: object) -> dict:
    respuesta = client.get("/api/panel/resumen", params=params, headers=headers)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def test_resumen_total_con_numeros_conocidos(
    client: TestClient, tokens: dict[str, dict[str, str]], panel_escenario: EscenarioPanel
) -> None:
    datos = _resumen(
        client,
        tokens["duenio"],
        desde=panel_escenario.desde.isoformat(),
        hasta=panel_escenario.hasta.isoformat(),
    )

    assert datos["ingresos_centavos"] == 40_000
    assert datos["egresos_operativos_centavos"] == 8_000
    assert datos["gastos_externos_centavos"] == 5_000
    assert datos["rentabilidad_neta_centavos"] == 27_000
    assert datos["rentabilidad_neta_motivo"] is None
    assert datos["egresos_operativos_sin_asignar_centavos"] == 0


def test_resumen_filtrado_por_servicio(
    client: TestClient, tokens: dict[str, dict[str, str]], panel_escenario: EscenarioPanel
) -> None:
    datos = _resumen(
        client,
        tokens["duenio"],
        desde=panel_escenario.desde.isoformat(),
        hasta=panel_escenario.hasta.isoformat(),
        servicio="GUARDERIA",
    )

    assert datos["ingresos_centavos"] == 28_000
    assert datos["gastos_externos_centavos"] == 5_000
    assert datos["egresos_operativos_centavos"] == 8_000
    assert datos["egresos_operativos_sin_asignar_centavos"] == 8_000
    assert datos["rentabilidad_neta_centavos"] == 23_000
    assert datos["rentabilidad_neta_motivo"] is not None


def test_resumen_filtrado_por_medio_no_calcula_rentabilidad(
    client: TestClient, tokens: dict[str, dict[str, str]], panel_escenario: EscenarioPanel
) -> None:
    datos = _resumen(
        client,
        tokens["duenio"],
        desde=panel_escenario.desde.isoformat(),
        hasta=panel_escenario.hasta.isoformat(),
        medio="DEBITO",
    )

    assert datos["ingresos_centavos"] == 12_000
    assert datos["rentabilidad_neta_centavos"] is None
    assert "medio de pago" in datos["rentabilidad_neta_motivo"]
    assert datos["egresos_operativos_centavos"] == 0


def test_periodo_inclusivo_en_los_bordes(
    client: TestClient, tokens: dict[str, dict[str, str]], panel_escenario: EscenarioPanel
) -> None:
    dia = panel_escenario.fecha.isoformat()
    datos = _resumen(
        client, tokens["duenio"], desde=dia, hasta=dia
    )
    # El reverso es de hoy, fuera de este día: quedan los pagos del día.
    assert datos["ingresos_centavos"] == 30_000 + 12_000

    siguiente = (panel_escenario.fecha + timedelta(days=1)).isoformat()
    ayer = (date.today() - timedelta(days=1)).isoformat()
    vacio = _resumen(client, tokens["duenio"], desde=siguiente, hasta=ayer)
    assert vacio["ingresos_centavos"] == 0


def test_egreso_anulado_no_suma(
    client: TestClient, tokens: dict[str, dict[str, str]], panel_escenario: EscenarioPanel
) -> None:
    datos = _resumen(
        client,
        tokens["duenio"],
        desde=panel_escenario.desde.isoformat(),
        hasta=panel_escenario.hasta.isoformat(),
    )
    assert datos["egresos_operativos_centavos"] == 8_000
    assert datos["gastos_externos_centavos"] == 5_000


def test_migracion_se_excluye_por_defecto_y_se_puede_incluir(
    client: TestClient,
    db_session: Session,
    tokens: dict[str, dict[str, str]],
    panel_escenario: EscenarioPanel,
) -> None:
    cargo = cobros_service.crear_cargo(
        db_session,
        persona_id=panel_escenario.persona_id,
        concepto="Migrado",
        total_centavos=6_000,
        tipo_servicio=TipoServicio.MIGRACION,
        origen=OrigenCargo.MIGRACION,
        usuario_id=panel_escenario.usuario_id,
    )
    cobros_service.registrar_pago(
        db_session,
        cargo_id=cargo.id,
        monto_centavos=6_000,
        medio="EFECTIVO",
        usuario_id=panel_escenario.usuario_id,
        fecha_pago=panel_escenario.fecha,
    )

    parametros = {
        "desde": panel_escenario.desde.isoformat(),
        "hasta": panel_escenario.hasta.isoformat(),
    }
    sin_migracion = _resumen(client, tokens["duenio"], **parametros)
    assert sin_migracion["ingresos_centavos"] == 40_000
    assert sin_migracion["ingresos_migracion_centavos"] == 6_000

    con_migracion = _resumen(
        client, tokens["duenio"], incluir_migracion=True, **parametros
    )
    assert con_migracion["ingresos_centavos"] == 46_000


def test_calidad_de_datos_cuenta_otro_y_migracion(
    client: TestClient,
    db_session: Session,
    tokens: dict[str, dict[str, str]],
    panel_escenario: EscenarioPanel,
) -> None:
    cobros_service.crear_cargo(
        db_session,
        persona_id=panel_escenario.persona_id,
        concepto="Sin clasificar",
        total_centavos=1_000,
        tipo_servicio=TipoServicio.OTRO,
        usuario_id=panel_escenario.usuario_id,
    )
    cobros_service.crear_cargo(
        db_session,
        persona_id=panel_escenario.persona_id,
        concepto="Migrado",
        total_centavos=1_000,
        tipo_servicio=TipoServicio.MIGRACION,
        origen=OrigenCargo.MIGRACION,
        usuario_id=panel_escenario.usuario_id,
    )

    datos = _resumen(
        client,
        tokens["duenio"],
        desde=panel_escenario.desde.isoformat(),
        hasta=panel_escenario.hasta.isoformat(),
    )
    assert datos["calidad_datos"]["cargos_otro"] == 1
    assert datos["calidad_datos"]["cargos_migrados"] == 1


def test_rango_maximo_de_settings(
    client: TestClient, tokens: dict[str, dict[str, str]] , panel_escenario: EscenarioPanel
) -> None:
    desde = date(2020, 1, 1)
    hasta = desde + timedelta(days=get_settings().panel_rango_max_dias)
    respuesta = client.get(
        "/api/panel/resumen",
        params={"desde": desde.isoformat(), "hasta": hasta.isoformat()},
        headers=tokens["duenio"],
    )
    assert respuesta.status_code == 422
