"""Gastos a externos (T-22): alta, listado, anulación y totales."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.cobros import service
from app.modules.padron import service as padron_service
from app.modules.padron.schemas import EmpleadoNuevo, PersonaNueva


def _auth_token(
    client: TestClient, username: str, password: str = "clave-de-prueba-segura"
) -> dict[str, str]:
    respuesta = client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )
    assert respuesta.status_code == 200
    token = respuesta.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@dataclass(frozen=True)
class EscenarioGastos:
    cargo_id: int
    sena_id: int


@pytest.fixture
def escenario_gastos(db_session: Session, referencias_cobros) -> EscenarioGastos:
    cargo = service.crear_cargo(
        db_session,
        persona_id=referencias_cobros.persona_id,
        concepto="Castración",
        total_centavos=200000,
        paciente_id=referencias_cobros.paciente_id,
        usuario_id=referencias_cobros.usuario_id,
    )
    sena = service.registrar_pago(
        db_session,
        cargo_id=cargo.id,
        monto_centavos=20000,
        medio="EFECTIVO",
        es_sena=True,
        usuario_id=referencias_cobros.usuario_id,
    )
    return EscenarioGastos(cargo_id=cargo.id, sena_id=sena.id)


def _crear_gasto(
    client: TestClient,
    headers: dict[str, str],
    referencias_cobros,
    **cambios,
) -> dict:
    cuerpo = {
        "empleado_id": referencias_cobros.empleado_id,
        "descripcion": "Cirugía de castración",
        "monto_centavos": 40000,
        "fecha": date.today().isoformat(),
    }
    cuerpo.update(cambios)
    return client.post("/api/gastos-externos", json=cuerpo, headers=headers)


def test_crear_gasto_vinculado_a_cargo_y_sena(
    client: TestClient,
    referencias_cobros,
    escenario_gastos: EscenarioGastos,
) -> None:
    headers = _auth_token(client, "duenio-cobros")
    respuesta = _crear_gasto(
        client,
        headers,
        referencias_cobros,
        cargo_id=escenario_gastos.cargo_id,
        pago_id=escenario_gastos.sena_id,
    )

    assert respuesta.status_code == 201
    data = respuesta.json()
    assert data["monto_centavos"] == 40000
    assert data["empleado_id"] == referencias_cobros.empleado_id
    assert data["empleado_nombre"] == "Veterinario Externo"
    assert data["cargo_id"] == escenario_gastos.cargo_id
    assert data["pago_id"] == escenario_gastos.sena_id
    assert data["registrado_por"] == referencias_cobros.usuario_id
    assert data["created_at"]
    assert data["anulado_en"] is None

    listado = client.get("/api/gastos-externos", headers=headers)
    assert listado.status_code == 200
    items = listado.json()["items"]
    assert [item["id"] for item in items] == [data["id"]]
    assert items[0]["empleado_nombre"] == "Veterinario Externo"


def test_empleado_interno_422(
    client: TestClient,
    db_session: Session,
    referencias_cobros,
) -> None:
    interno = padron_service.crear_empleado(
        db_session,
        EmpleadoNuevo(
            persona=PersonaNueva(
                nombre="Recepción",
                apellido="Interna",
                dni="30999888",
                telefonos=["11 5555-0202"],
            ),
            tipo="INTERNO",
        ),
    )
    headers = _auth_token(client, "duenio-cobros")
    respuesta = _crear_gasto(
        client, headers, referencias_cobros, empleado_id=interno.persona_id
    )
    assert respuesta.status_code == 422


def test_empleado_inexistente_422(client: TestClient, referencias_cobros) -> None:
    headers = _auth_token(client, "duenio-cobros")
    respuesta = _crear_gasto(
        client, headers, referencias_cobros, empleado_id=999999
    )
    assert respuesta.status_code == 422


@pytest.mark.parametrize("monto", [0, -100, 40000.5])
def test_monto_invalido_422(
    client: TestClient, referencias_cobros, monto: int | float
) -> None:
    headers = _auth_token(client, "duenio-cobros")
    respuesta = _crear_gasto(
        client, headers, referencias_cobros, monto_centavos=monto
    )
    assert respuesta.status_code == 422


@pytest.mark.parametrize("descripcion", ["", "   "])
def test_descripcion_vacia_422(
    client: TestClient, referencias_cobros, descripcion: str
) -> None:
    headers = _auth_token(client, "duenio-cobros")
    respuesta = _crear_gasto(
        client, headers, referencias_cobros, descripcion=descripcion
    )
    assert respuesta.status_code == 422


def test_fecha_futura_422(client: TestClient, referencias_cobros) -> None:
    headers = _auth_token(client, "duenio-cobros")
    respuesta = _crear_gasto(
        client,
        headers,
        referencias_cobros,
        fecha=(date.today() + timedelta(days=1)).isoformat(),
    )
    assert respuesta.status_code == 422


def test_reloj_inyectable_rechaza_fecha_futura(
    db_session: Session, referencias_cobros
) -> None:
    with pytest.raises(service.CobrosError):
        service.registrar_gasto_externo(
            db_session,
            empleado_externo_id=referencias_cobros.empleado_id,
            descripcion="Cirugía",
            monto_centavos=40000,
            fecha=date(2026, 1, 11),
            usuario_id=referencias_cobros.usuario_id,
            reloj=lambda: date(2026, 1, 10),
        )


def test_pago_que_no_es_sena_422(
    client: TestClient,
    db_session: Session,
    referencias_cobros,
    escenario_gastos: EscenarioGastos,
) -> None:
    pago = service.registrar_pago(
        db_session,
        cargo_id=escenario_gastos.cargo_id,
        monto_centavos=10000,
        medio="EFECTIVO",
        usuario_id=referencias_cobros.usuario_id,
    )
    headers = _auth_token(client, "duenio-cobros")
    respuesta = _crear_gasto(
        client,
        headers,
        referencias_cobros,
        cargo_id=escenario_gastos.cargo_id,
        pago_id=pago.id,
    )
    assert respuesta.status_code == 422


def test_sena_de_otro_cargo_422(
    client: TestClient,
    db_session: Session,
    referencias_cobros,
    escenario_gastos: EscenarioGastos,
) -> None:
    otro_cargo = service.crear_cargo(
        db_session,
        persona_id=referencias_cobros.persona_id,
        concepto="Otro servicio",
        total_centavos=100000,
        usuario_id=referencias_cobros.usuario_id,
    )
    headers = _auth_token(client, "duenio-cobros")
    respuesta = _crear_gasto(
        client,
        headers,
        referencias_cobros,
        cargo_id=otro_cargo.id,
        pago_id=escenario_gastos.sena_id,
    )
    assert respuesta.status_code == 422


def test_gasto_suelto_permitido(
    client: TestClient, referencias_cobros
) -> None:
    headers = _auth_token(client, "duenio-cobros")
    respuesta = _crear_gasto(
        client, headers, referencias_cobros, descripcion="Honorarios sueltos"
    )
    assert respuesta.status_code == 201
    assert respuesta.json()["cargo_id"] is None
    assert respuesta.json()["pago_id"] is None


def test_filtros_y_total_solo_suma_no_anulados(
    client: TestClient,
    db_session: Session,
    referencias_cobros,
    escenario_gastos: EscenarioGastos,
) -> None:
    headers = _auth_token(client, "duenio-cobros")
    hoy = date.today()

    def crear(fecha: date, monto: int, cargo_id: int | None = None) -> int:
        respuesta = _crear_gasto(
            client,
            headers,
            referencias_cobros,
            fecha=fecha.isoformat(),
            monto_centavos=monto,
            cargo_id=cargo_id,
        )
        assert respuesta.status_code == 201
        return respuesta.json()["id"]

    id_viejo = crear(hoy - timedelta(days=10), 10000)
    id_medio = crear(hoy - timedelta(days=5), 20000)
    id_cargo = crear(hoy, 30000, cargo_id=escenario_gastos.cargo_id)
    anulado = client.post(
        f"/api/gastos-externos/{id_cargo}/anular",
        json={"motivo": "Se cargó dos veces"},
        headers=headers,
    )
    assert anulado.status_code == 200

    por_periodo = client.get(
        "/api/gastos-externos",
        params={
            "desde": (hoy - timedelta(days=6)).isoformat(),
            "hasta": hoy.isoformat(),
        },
        headers=headers,
    )
    assert por_periodo.status_code == 200
    assert [item["id"] for item in por_periodo.json()["items"]] == [
        id_cargo,
        id_medio,
    ]
    assert por_periodo.json()["total_centavos"] == 20000

    por_cargo = client.get(
        "/api/gastos-externos",
        params={"cargo_id": escenario_gastos.cargo_id},
        headers=headers,
    )
    assert por_cargo.json()["total_centavos"] == 0
    assert [item["id"] for item in por_cargo.json()["items"]] == [id_cargo]

    por_empleado = client.get(
        "/api/gastos-externos",
        params={"empleado_id": referencias_cobros.empleado_id},
        headers=headers,
    )
    assert por_empleado.json()["total_centavos"] == 30000

    total = service.total_gastos_externos(
        db_session, desde=hoy - timedelta(days=10), hasta=hoy
    )
    assert total == 30000

    ids = {item["id"] for item in por_periodo.json()["items"]}
    assert id_viejo not in ids


def test_anular_audita_deja_de_sumar_y_no_se_reanula(
    client: TestClient, referencias_cobros
) -> None:
    headers = _auth_token(client, "duenio-cobros")
    creado = _crear_gasto(client, headers, referencias_cobros)
    gasto_id = creado.json()["id"]

    sin_motivo = client.post(
        f"/api/gastos-externos/{gasto_id}/anular",
        json={"motivo": "   "},
        headers=headers,
    )
    assert sin_motivo.status_code == 422

    anulado = client.post(
        f"/api/gastos-externos/{gasto_id}/anular",
        json={"motivo": "Monto mal cargado"},
        headers=headers,
    )
    assert anulado.status_code == 200
    data = anulado.json()
    assert data["motivo_anulacion"] == "Monto mal cargado"
    assert data["anulado_por"] == referencias_cobros.usuario_id
    assert data["anulado_en"] is not None

    listado = client.get("/api/gastos-externos", headers=headers)
    assert [item["id"] for item in listado.json()["items"]] == [gasto_id]
    assert listado.json()["total_centavos"] == 0

    de_nuevo = client.post(
        f"/api/gastos-externos/{gasto_id}/anular",
        json={"motivo": "Otra vez"},
        headers=headers,
    )
    assert de_nuevo.status_code == 409


def test_no_existe_endpoint_para_editar_ni_borrar(
    client: TestClient, referencias_cobros
) -> None:
    headers = _auth_token(client, "duenio-cobros")
    gasto_id = _crear_gasto(client, headers, referencias_cobros).json()["id"]

    assert (
        client.put(
            f"/api/gastos-externos/{gasto_id}", json={}, headers=headers
        ).status_code
        == 405
    )
    assert (
        client.delete(f"/api/gastos-externos/{gasto_id}", headers=headers).status_code
        == 405
    )


def test_obtener_gasto_inexistente_404(
    client: TestClient, referencias_cobros
) -> None:
    headers = _auth_token(client, "duenio-cobros")
    respuesta = client.get("/api/gastos-externos/999999", headers=headers)
    assert respuesta.status_code == 404
