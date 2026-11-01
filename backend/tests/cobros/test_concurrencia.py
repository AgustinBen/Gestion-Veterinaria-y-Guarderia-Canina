"""Concurrencia de pagos (T-19, issue #57).

Dos sesiones reales en hilos distintos sobre la misma base de archivo. El
`BEGIN IMMEDIATE` de `service.registrar_pago` es lo que serializa la lectura
del saldo y la escritura del pago.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

from sqlalchemy.orm import Session, sessionmaker

from app.modules.cobros import repository, service


def _correr_en_paralelo(acciones: list[Callable[[Session], None]], engine_sqlite) -> tuple[dict[int, str], list[int]]:
    SessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine_sqlite, future=True
    )
    barrera = threading.Barrier(len(acciones))
    resultados: dict[int, str] = {}
    cruzaron: list[int] = []

    def ejecutar(indice: int, accion: Callable[[Session], None]) -> None:
        sesion = SessionLocal()
        try:
            barrera.wait(timeout=5)
            cruzaron.append(indice)
            accion(sesion)
            resultados[indice] = "ok"
        except Exception as exc:  # el test compara nombres de excepción
            resultados[indice] = type(exc).__name__
        finally:
            sesion.close()

    hilos = [
        threading.Thread(target=ejecutar, args=(indice, accion))
        for indice, accion in enumerate(acciones)
    ]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(timeout=10)
    assert not any(hilo.is_alive() for hilo in hilos), "Un hilo no terminó a tiempo"
    return resultados, cruzaron


def test_dos_pagos_simultaneos_no_sobrepasan_el_saldo(
    engine_sqlite,
    db_session: Session,
    referencias_cobros,
    monkeypatch,
) -> None:
    cargo = service.crear_cargo(
        db_session,
        persona_id=referencias_cobros.persona_id,
        concepto="Guardería",
        total_centavos=5000,
        paciente_id=referencias_cobros.paciente_id,
        usuario_id=referencias_cobros.usuario_id,
    )
    cargo_id = cargo.id
    usuario_id = referencias_cobros.usuario_id

    saldo_original = repository.saldo

    def saldo_con_pausa(db: Session, cargo_id: int) -> int:
        valor = saldo_original(db, cargo_id)
        # Amplía la ventana entre la lectura del saldo y la escritura.
        time.sleep(0.3)
        return valor

    monkeypatch.setattr(repository, "saldo", saldo_con_pausa)

    def pagar(sesion: Session) -> None:
        service.registrar_pago(
            sesion,
            cargo_id=cargo_id,
            monto_centavos=3000,
            medio="EFECTIVO",
            usuario_id=usuario_id,
        )

    resultados, cruzaron = _correr_en_paralelo([pagar, pagar], engine_sqlite)

    assert sorted(cruzaron) == [0, 1]
    assert sorted(resultados.values()) == ["SaldoInsuficiente", "ok"], resultados

    sesion_final = sessionmaker(bind=engine_sqlite, future=True)()
    try:
        assert saldo_original(sesion_final, cargo_id) == 2000
    finally:
        sesion_final.close()


def test_misma_clave_simultanea_devuelve_un_solo_pago(
    engine_sqlite,
    db_session: Session,
    referencias_cobros,
) -> None:
    cargo = service.crear_cargo(
        db_session,
        persona_id=referencias_cobros.persona_id,
        concepto="Guardería",
        total_centavos=5000,
        paciente_id=referencias_cobros.paciente_id,
        usuario_id=referencias_cobros.usuario_id,
    )
    cargo_id = cargo.id
    usuario_id = referencias_cobros.usuario_id
    pagos: list[int] = []
    candado = threading.Lock()

    def pagar(sesion: Session) -> None:
        pago = service.registrar_pago(
            sesion,
            cargo_id=cargo_id,
            monto_centavos=3000,
            medio="EFECTIVO",
            usuario_id=usuario_id,
            clave_idempotencia="misma-clave-simultanea",
        )
        with candado:
            pagos.append(pago.id)

    resultados, cruzaron = _correr_en_paralelo([pagar, pagar], engine_sqlite)

    assert sorted(cruzaron) == [0, 1]
    assert set(resultados.values()) == {"ok"}, resultados
    assert len(pagos) == 2
    assert pagos[0] == pagos[1]

    sesion_final = sessionmaker(bind=engine_sqlite, future=True)()
    try:
        assert repository.saldo(sesion_final, cargo_id) == 2000
    finally:
        sesion_final.close()
