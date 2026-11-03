"""Egresos operativos y categorías del panel (T-38)."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.panel import models as panel_models
from tests.panel.conftest import EscenarioPanel


def _categoria(client: TestClient, headers: dict[str, str], nombre: str) -> dict:
    respuesta = client.post(
        "/api/categorias-egreso", json={"nombre": nombre}, headers=headers
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def test_crear_listar_y_actualizar_categorias(
    client: TestClient,
    tokens: dict[str, dict[str, str]],
    panel_escenario: EscenarioPanel,
) -> None:
    creada = _categoria(client, tokens["duenio"], "Insumos")
    assert creada["activa"] is True

    listado = client.get("/api/categorias-egreso", headers=tokens["duenio"])
    assert listado.status_code == 200
    assert any(item["nombre"] == "Insumos" for item in listado.json())

    respuesta = client.patch(
        f"/api/categorias-egreso/{creada['id']}",
        json={"activa": False},
        headers=tokens["duenio"],
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["activa"] is False


def test_categoria_repetida_409(
    client: TestClient,
    tokens: dict[str, dict[str, str]],
    panel_escenario: EscenarioPanel,
) -> None:
    _categoria(client, tokens["duenio"], "Insumos")
    repetida = client.post(
        "/api/categorias-egreso", json={"nombre": "  insumos "}, headers=tokens["duenio"]
    )
    assert repetida.status_code == 409


def test_alta_de_egreso_en_centavos_y_listado(
    client: TestClient,
    tokens: dict[str, dict[str, str]],
    panel_escenario: EscenarioPanel,
) -> None:
    categoria = _categoria(client, tokens["duenio"], "Insumos")
    hoy = date.today()
    alta = client.post(
        "/api/egresos",
        json={
            "fecha": hoy.isoformat(),
            "monto_centavos": 2_700_000,
            "categoria_id": categoria["id"],
            "descripcion": "Alimento",
        },
        headers=tokens["duenio"],
    )
    assert alta.status_code == 201, alta.text
    assert alta.json()["monto_centavos"] == 2_700_000
    assert alta.json()["categoria_nombre"] == "Insumos"

    listado = client.get(
        "/api/egresos",
        params={"desde": hoy.isoformat(), "hasta": hoy.isoformat()},
        headers=tokens["duenio"],
    )
    assert listado.status_code == 200
    assert [item["descripcion"] for item in listado.json()] == ["Alimento"]


def test_sin_categorias_no_permite_egresos(
    client: TestClient,
    tokens: dict[str, dict[str, str]],
    panel_escenario: EscenarioPanel,
    db_session: Session,
) -> None:
    db_session.query(panel_models.Egreso).delete()
    db_session.query(panel_models.CategoriaEgreso).delete()
    db_session.commit()

    respuesta = client.post(
        "/api/egresos",
        json={
            "fecha": date.today().isoformat(),
            "monto_centavos": 1_000,
            "categoria_id": 1,
            "descripcion": "Luz",
        },
        headers=tokens["duenio"],
    )
    assert respuesta.status_code == 422
    assert "categoría" in respuesta.json()["detail"].lower()


def test_categoria_inactiva_y_fecha_futura_422(
    client: TestClient,
    tokens: dict[str, dict[str, str]],
    panel_escenario: EscenarioPanel,
) -> None:
    categoria = _categoria(client, tokens["duenio"], "Insumos")
    client.patch(
        f"/api/categorias-egreso/{categoria['id']}",
        json={"activa": False},
        headers=tokens["duenio"],
    )
    inactiva = client.post(
        "/api/egresos",
        json={
            "fecha": date.today().isoformat(),
            "monto_centavos": 1_000,
            "categoria_id": categoria["id"],
            "descripcion": "Luz",
        },
        headers=tokens["duenio"],
    )
    assert inactiva.status_code == 422

    otra = _categoria(client, tokens["duenio"], "Servicios")
    futura = client.post(
        "/api/egresos",
        json={
            "fecha": (date.today() + timedelta(days=1)).isoformat(),
            "monto_centavos": 1_000,
            "categoria_id": otra["id"],
            "descripcion": "Luz",
        },
        headers=tokens["duenio"],
    )
    assert futura.status_code == 422


def test_montos_invalidos_422(
    client: TestClient,
    tokens: dict[str, dict[str, str]],
    panel_escenario: EscenarioPanel,
) -> None:
    categoria = _categoria(client, tokens["duenio"], "Insumos")
    for monto in (0, -100, 10.5):
        respuesta = client.post(
            "/api/egresos",
            json={
                "fecha": date.today().isoformat(),
                "monto_centavos": monto,
                "categoria_id": categoria["id"],
                "descripcion": "Luz",
            },
            headers=tokens["duenio"],
        )
        assert respuesta.status_code == 422, monto


def test_anular_exige_motivo_y_no_se_repite(
    client: TestClient,
    tokens: dict[str, dict[str, str]],
    panel_escenario: EscenarioPanel,
) -> None:
    categoria = _categoria(client, tokens["duenio"], "Insumos")
    alta = client.post(
        "/api/egresos",
        json={
            "fecha": date.today().isoformat(),
            "monto_centavos": 5_000,
            "categoria_id": categoria["id"],
            "descripcion": "Luz",
        },
        headers=tokens["duenio"],
    )
    egreso_id = alta.json()["id"]

    sin_motivo = client.post(
        f"/api/egresos/{egreso_id}/anular",
        json={"motivo": ""},
        headers=tokens["duenio"],
    )
    assert sin_motivo.status_code == 422

    anulado = client.post(
        f"/api/egresos/{egreso_id}/anular",
        json={"motivo": "Carga duplicada"},
        headers=tokens["duenio"],
    )
    assert anulado.status_code == 200
    assert anulado.json()["motivo_anulacion"] == "Carga duplicada"

    repetido = client.post(
        f"/api/egresos/{egreso_id}/anular",
        json={"motivo": "Otra vez"},
        headers=tokens["duenio"],
    )
    assert repetido.status_code == 409


def test_permisos_de_egresos(
    client: TestClient,
    tokens: dict[str, dict[str, str]],
    panel_escenario: EscenarioPanel,
) -> None:
    assert client.get("/api/egresos").status_code == 401
    assert client.get("/api/categorias-egreso").status_code == 401
    for rol in ("personal", "veterinario"):
        assert (
            client.get("/api/egresos", headers=tokens[rol]).status_code == 403
        )
        assert (
            client.get("/api/categorias-egreso", headers=tokens[rol]).status_code
            == 403
        )
        assert (
            client.post(
                "/api/categorias-egreso",
                json={"nombre": "Insumos"},
                headers=tokens[rol],
            ).status_code
            == 403
        )
