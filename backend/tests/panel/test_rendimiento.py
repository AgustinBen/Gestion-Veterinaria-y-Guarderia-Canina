"""Rendimiento del panel con 10.000 pagos sembrados (T-46)."""

from __future__ import annotations

import time

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.cobros import service as cobros_service
from tests.panel.conftest import EscenarioPanel


def test_endpoints_del_panel_bajo_un_segundo(
    client: TestClient,
    db_session: Session,
    tokens: dict[str, dict[str, str]],
    panel_escenario: EscenarioPanel,
) -> None:
    medio = cobros_service.listar_medios_pago(db_session)[0]
    filas = [
        {
            "cargo_id": panel_escenario.cargo_consulta_id,
            "monto": 100,
            "tipo": "PAGO",
            "medio_pago_id": medio.id,
            "es_sena": 0,
            "fecha": panel_escenario.fecha.isoformat(),
            "usuario_id": panel_escenario.usuario_id,
        }
        for _ in range(10_000)
    ]
    db_session.execute(
        text(
            "INSERT INTO pago "
            "(cargo_id, monto, tipo, medio_pago_id, es_sena, fecha, usuario_id) "
            "VALUES (:cargo_id, :monto, :tipo, :medio_pago_id, :es_sena, :fecha, :usuario_id)"
        ),
        filas,
    )
    db_session.commit()

    parametros = {
        "desde": panel_escenario.desde.isoformat(),
        "hasta": panel_escenario.hasta.isoformat(),
    }
    rutas = [
        ("/api/panel/resumen", parametros),
        ("/api/panel/serie", {**parametros, "agrupar": "dia"}),
        ("/api/panel/ingresos-por-servicio", parametros),
        ("/api/panel/ingresos-por-medio", parametros),
        ("/api/panel/deudas", {}),
    ]
    for ruta, params in rutas:
        inicio = time.perf_counter()
        respuesta = client.get(ruta, params=params, headers=tokens["duenio"])
        transcurrido = time.perf_counter() - inicio
        assert respuesta.status_code == 200, ruta
        assert transcurrido < 1.0, f"{ruta} tardó {transcurrido:.3f}s"
