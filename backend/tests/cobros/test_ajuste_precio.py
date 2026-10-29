"""Tests del ajuste de precio de cargos (RN-22)."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.modules.cobros import repository, service
from app.modules.cobros.dinero import formatear_pesos
from app.modules.identidad import service as identidad_service
from app.modules.identidad.permisos import Rol
from app.modules.identidad.schemas import UsuarioCrear


def _auth_token(
    client: TestClient,
    username: str,
    password: str = "clave-de-prueba-segura",
) -> dict[str, str]:
    respuesta = client.post("/api/auth/login", json={"username": username, "password": password})
    assert respuesta.status_code == 200
    token = respuesta.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _crear_cargo(
    client: TestClient,
    headers: dict[str, str],
    referencias_cobros,
    total_centavos: int = 30000,
) -> int:
    respuesta = client.post(
        "/api/cargos",
        json={
            "persona_id": referencias_cobros.persona_id,
            "concepto": "Servicio",
            "total_centavos": total_centavos,
            "paciente_id": referencias_cobros.paciente_id,
        },
        headers=headers,
    )
    assert respuesta.status_code == 201
    return respuesta.json()["id"]


def _pagar(
    client: TestClient,
    headers: dict[str, str],
    cargo_id: int,
    monto_centavos: int,
    es_sena: bool = False,
) -> dict:
    respuesta = client.post(
        f"/api/cargos/{cargo_id}/pagos",
        json={"monto_centavos": monto_centavos, "medio": "EFECTIVO", "es_sena": es_sena},
        headers=headers,
    )
    assert respuesta.status_code == 200
    return respuesta.json()


def _ajustar(
    client: TestClient,
    headers: dict[str, str],
    cargo_id: int,
    nuevo_total_centavos: int,
    motivo: str = "Ajuste de precio",
):
    return client.post(
        f"/api/cargos/{cargo_id}/ajustes",
        json={"nuevo_total_centavos": nuevo_total_centavos, "motivo": motivo},
        headers=headers,
    )


def _crear_usuario(db_session: Session, username: str, rol: Rol) -> None:
    identidad_service.crear_usuario(
        db_session,
        UsuarioCrear(username=username, password="clave-de-prueba-segura", rol=rol),
    )


def test_ajuste_baja_total_y_registra_auditoria(
    client: TestClient,
    referencias_cobros,
) -> None:
    headers = _auth_token(client, "duenio-cobros")
    cargo_id = _crear_cargo(client, headers, referencias_cobros)
    _pagar(client, headers, cargo_id, 10000, es_sena=True)
    _pagar(client, headers, cargo_id, 15000)

    respuesta = _ajustar(client, headers, cargo_id, 28000, motivo="Descuento")
    assert respuesta.status_code == 200
    data = respuesta.json()
    assert data["cargo_id"] == cargo_id
    assert data["precio_anterior"] == 30000
    assert data["precio_nuevo"] == 28000
    assert data["motivo"] == "Descuento"
    assert data["usuario_id"] == referencias_cobros.usuario_id
    assert data["created_at"]

    detalle = client.get(f"/api/cargos/{cargo_id}", headers=headers).json()
    assert detalle["total_inicial"] == 30000
    assert detalle["total_vigente"] == 28000
    assert detalle["total_pagado"] == 25000
    assert detalle["saldo"] == 3000

    historial = client.get(f"/api/cargos/{cargo_id}/ajustes", headers=headers)
    assert historial.status_code == 200
    assert len(historial.json()) == 1


def test_ajuste_menor_a_lo_pagado_422_y_no_guarda(
    client: TestClient,
    referencias_cobros,
) -> None:
    headers = _auth_token(client, "duenio-cobros")
    cargo_id = _crear_cargo(client, headers, referencias_cobros)
    _pagar(client, headers, cargo_id, 10000, es_sena=True)
    _pagar(client, headers, cargo_id, 15000)

    respuesta = _ajustar(client, headers, cargo_id, 24000)
    assert respuesta.status_code == 422
    assert formatear_pesos(25000) in respuesta.text

    historial = client.get(f"/api/cargos/{cargo_id}/ajustes", headers=headers)
    assert historial.json() == []


def test_ajuste_igual_a_lo_pagado_salda_y_luego_422(
    client: TestClient,
    referencias_cobros,
) -> None:
    headers = _auth_token(client, "duenio-cobros")
    cargo_id = _crear_cargo(client, headers, referencias_cobros)
    _pagar(client, headers, cargo_id, 10000, es_sena=True)
    _pagar(client, headers, cargo_id, 15000)

    respuesta = _ajustar(client, headers, cargo_id, 25000)
    assert respuesta.status_code == 200
    detalle = client.get(f"/api/cargos/{cargo_id}", headers=headers).json()
    assert detalle["saldo"] == 0

    posterior = _ajustar(client, headers, cargo_id, 26000)
    assert posterior.status_code == 422
    assert "pagado por completo" in posterior.text


def test_cargo_sin_saldo_422(
    client: TestClient,
    referencias_cobros,
) -> None:
    headers = _auth_token(client, "duenio-cobros")
    cargo_id = _crear_cargo(client, headers, referencias_cobros, total_centavos=10000)
    _pagar(client, headers, cargo_id, 10000)

    respuesta = _ajustar(client, headers, cargo_id, 20000)
    assert respuesta.status_code == 422
    assert "pagado por completo" in respuesta.text


def test_sena_unica_permite_subir_y_bajar(
    client: TestClient,
    referencias_cobros,
) -> None:
    headers = _auth_token(client, "duenio-cobros")
    cargo_id = _crear_cargo(client, headers, referencias_cobros)
    _pagar(client, headers, cargo_id, 10000, es_sena=True)

    subir = _ajustar(client, headers, cargo_id, 40000)
    assert subir.status_code == 200
    bajar = _ajustar(client, headers, cargo_id, 20000)
    assert bajar.status_code == 200

    detalle = client.get(f"/api/cargos/{cargo_id}", headers=headers).json()
    assert detalle["total_inicial"] == 30000
    assert detalle["total_vigente"] == 20000
    assert detalle["total_pagado"] == 10000
    assert detalle["saldo"] == 10000


def test_dos_ajustes_encadenan_anterior_e_historial_ordenado(
    client: TestClient,
    referencias_cobros,
) -> None:
    headers = _auth_token(client, "duenio-cobros")
    cargo_id = _crear_cargo(client, headers, referencias_cobros)

    assert _ajustar(client, headers, cargo_id, 35000).status_code == 200
    assert _ajustar(client, headers, cargo_id, 32000).status_code == 200

    historial = client.get(f"/api/cargos/{cargo_id}/ajustes", headers=headers)
    assert historial.status_code == 200
    filas = historial.json()
    assert [fila["precio_anterior"] for fila in filas] == [30000, 35000]
    assert [fila["precio_nuevo"] for fila in filas] == [35000, 32000]

    detalle = client.get(f"/api/cargos/{cargo_id}", headers=headers).json()
    assert detalle["total_vigente"] == 32000


def test_validaciones_422(
    client: TestClient,
    referencias_cobros,
) -> None:
    headers = _auth_token(client, "duenio-cobros")
    cargo_id = _crear_cargo(client, headers, referencias_cobros)

    sin_motivo = client.post(
        f"/api/cargos/{cargo_id}/ajustes",
        json={"nuevo_total_centavos": 35000},
        headers=headers,
    )
    assert sin_motivo.status_code == 422

    motivo_vacio = _ajustar(client, headers, cargo_id, 35000, motivo="")
    assert motivo_vacio.status_code == 422
    assert "motivo" in motivo_vacio.text

    motivo_espacios = _ajustar(client, headers, cargo_id, 35000, motivo="   ")
    assert motivo_espacios.status_code == 422
    assert "Falta el motivo" in motivo_espacios.text

    mismo_total = _ajustar(client, headers, cargo_id, 30000)
    assert mismo_total.status_code == 422
    assert "igual al total vigente" in mismo_total.text

    cero = _ajustar(client, headers, cargo_id, 0)
    assert cero.status_code == 422

    negativo = _ajustar(client, headers, cargo_id, -100)
    assert negativo.status_code == 422

    assert client.get(f"/api/cargos/{cargo_id}/ajustes", headers=headers).json() == []


def test_cargo_inexistente_404(
    client: TestClient,
    referencias_cobros,
) -> None:
    headers = _auth_token(client, "duenio-cobros")

    respuesta = _ajustar(client, headers, 999999, 35000)
    assert respuesta.status_code == 404

    historial = client.get("/api/cargos/999999/ajustes", headers=headers)
    assert historial.status_code == 404


def test_reverso_previo_descuenta_de_lo_pagado(
    client: TestClient,
    referencias_cobros,
) -> None:
    headers = _auth_token(client, "duenio-cobros")
    cargo_id = _crear_cargo(client, headers, referencias_cobros)
    _pagar(client, headers, cargo_id, 10000, es_sena=True)
    pago = _pagar(client, headers, cargo_id, 15000)

    reverso = client.post(
        f"/api/pagos/{pago['id']}/revertir",
        json={"motivo": "Error de carga"},
        headers=headers,
    )
    assert reverso.status_code == 200

    permitido = _ajustar(client, headers, cargo_id, 12000)
    assert permitido.status_code == 200

    rechazado = _ajustar(client, headers, cargo_id, 9000)
    assert rechazado.status_code == 422
    assert formatear_pesos(10000) in rechazado.text


def test_matriz_de_roles(
    client: TestClient,
    referencias_cobros,
    db_session: Session,
) -> None:
    _crear_usuario(db_session, "personal-ajuste", Rol.PERSONAL)
    _crear_usuario(db_session, "vet-ajuste", Rol.VETERINARIO)

    headers_duenio = _auth_token(client, "duenio-cobros")
    headers_personal = _auth_token(client, "personal-ajuste")
    headers_vet = _auth_token(client, "vet-ajuste")

    cargo_duenio = _crear_cargo(client, headers_duenio, referencias_cobros)
    assert _ajustar(client, headers_duenio, cargo_duenio, 28000).status_code == 200

    cargo_personal = _crear_cargo(client, headers_personal, referencias_cobros)
    assert _ajustar(client, headers_personal, cargo_personal, 35000).status_code == 200

    bajar_personal = _ajustar(client, headers_personal, cargo_personal, 28000)
    assert bajar_personal.status_code == 403
    assert "Solo el Dueño" in bajar_personal.text

    cargo_vet = _crear_cargo(client, headers_duenio, referencias_cobros)
    assert _ajustar(client, headers_vet, cargo_vet, 35000).status_code == 403
    assert _ajustar(client, headers_vet, cargo_vet, 28000).status_code == 403

    sin_token = client.post(
        f"/api/cargos/{cargo_vet}/ajustes",
        json={"nuevo_total_centavos": 35000, "motivo": "Ajuste"},
    )
    assert sin_token.status_code == 401

    assert client.get(f"/api/cargos/{cargo_duenio}/ajustes", headers=headers_duenio).status_code == 200
    assert client.get(f"/api/cargos/{cargo_personal}/ajustes", headers=headers_personal).status_code == 200
    assert client.get(f"/api/cargos/{cargo_vet}/ajustes", headers=headers_vet).status_code == 403
    assert client.get(f"/api/cargos/{cargo_vet}/ajustes").status_code == 401


def test_service_ajustar_precio_queda_disponible_para_otros_modulos(
    db_session: Session,
    referencias_cobros,
) -> None:
    cargo = service.crear_cargo(
        db_session,
        persona_id=referencias_cobros.persona_id,
        concepto="Guardería",
        total_centavos=30000,
        paciente_id=referencias_cobros.paciente_id,
        usuario_id=referencias_cobros.usuario_id,
    )

    ajuste = service.ajustar_precio(
        db_session,
        cargo_id=cargo.id,
        nuevo_total_centavos=35000,
        motivo="Ajuste desde guardería",
        usuario_id=referencias_cobros.usuario_id,
        rol=Rol.DUENIO,
    )

    assert ajuste.precio_anterior == 30000
    assert ajuste.precio_nuevo == 35000
    detalle = service.obtener_cargo_detalle(db_session, cargo.id)
    assert detalle["total_vigente"] == 35000


def test_ajuste_falla_y_no_persiste_si_no_puede_iniciar_transaccion(
    db_session: Session,
    referencias_cobros,
) -> None:
    cargo = service.crear_cargo(
        db_session,
        persona_id=referencias_cobros.persona_id,
        concepto="Guardería",
        total_centavos=30000,
        paciente_id=referencias_cobros.paciente_id,
        usuario_id=referencias_cobros.usuario_id,
    )
    conexion = db_session.connection()
    conexion.exec_driver_sql("BEGIN")

    with pytest.raises(service.TransaccionNoDisponible) as error:
        service.ajustar_precio(
            db_session,
            cargo_id=cargo.id,
            nuevo_total_centavos=35000,
            motivo="Ajuste sin bloqueo",
            usuario_id=referencias_cobros.usuario_id,
            rol=Rol.DUENIO,
        )

    assert isinstance(error.value.__cause__, SQLAlchemyError)
    assert "Intente nuevamente" in str(error.value)
    assert repository.ajustes_de_cargo(db_session, cargo.id) == []


def test_concurrencia_pago_y_ajuste(
    engine_sqlite,
    db_session: Session,
    referencias_cobros,
    monkeypatch,
) -> None:
    cargo = service.crear_cargo(
        db_session,
        persona_id=referencias_cobros.persona_id,
        concepto="Guardería",
        total_centavos=30000,
        paciente_id=referencias_cobros.paciente_id,
        usuario_id=referencias_cobros.usuario_id,
    )
    service.registrar_pago(
        db_session,
        cargo_id=cargo.id,
        monto_centavos=10000,
        medio="EFECTIVO",
        es_sena=True,
        usuario_id=referencias_cobros.usuario_id,
    )

    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine_sqlite,
        future=True,
    )
    total_pagado_original = repository.total_pagado

    def total_pagado_con_pausa(db: Session, cargo_id: int) -> int:
        valor = total_pagado_original(db, cargo_id)
        # Amplía la ventana de carrera entre la lectura y la escritura.
        time.sleep(0.3)
        return valor

    monkeypatch.setattr(repository, "total_pagado", total_pagado_con_pausa)

    barrera = threading.Barrier(2)
    resultados: dict[str, str] = {}
    errores: dict[str, str] = {}

    def ejecutar(nombre: str, accion: Callable[[Session], None]) -> None:
        sesion = SessionLocal()
        try:
            barrera.wait(timeout=5)
            accion(sesion)
            resultados[nombre] = "ok"
        except Exception as exc:
            errores[nombre] = type(exc).__name__
        finally:
            sesion.close()

    def pagar(sesion: Session) -> None:
        service.registrar_pago(
            sesion,
            cargo_id=cargo.id,
            monto_centavos=15000,
            medio="EFECTIVO",
            usuario_id=referencias_cobros.usuario_id,
        )

    def ajustar(sesion: Session) -> None:
        service.ajustar_precio(
            sesion,
            cargo_id=cargo.id,
            nuevo_total_centavos=20000,
            motivo="Ajuste concurrente",
            usuario_id=referencias_cobros.usuario_id,
            rol=Rol.DUENIO,
        )

    hilos = [
        threading.Thread(target=ejecutar, args=("pago", pagar)),
        threading.Thread(target=ejecutar, args=("ajuste", ajustar)),
    ]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(timeout=10)

    # Con BEGIN IMMEDIATE exactamente una operación gana; la otra se rechaza.
    assert len(resultados) == 1, errores
    assert len(errores) == 1, resultados

    sesion_final = SessionLocal()
    try:
        total_vigente = repository.total_vigente(sesion_final, cargo.id)
        total_pagado = total_pagado_original(sesion_final, cargo.id)
    finally:
        sesion_final.close()

    assert total_vigente >= total_pagado
