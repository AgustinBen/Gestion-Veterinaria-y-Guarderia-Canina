from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.modules.cobros import dinero, models, repository, seed


def _crear_triggers(db_session):
    db_session.execute(text("CREATE TRIGGER IF NOT EXISTS trg_cargo_no_update BEFORE UPDATE ON cargo BEGIN SELECT RAISE(ABORT, 'cargo es inmutable'); END;"))
    db_session.execute(text("CREATE TRIGGER IF NOT EXISTS trg_cargo_no_delete BEFORE DELETE ON cargo BEGIN SELECT RAISE(ABORT, 'cargo es inmutable'); END;"))
    db_session.execute(text("CREATE TRIGGER IF NOT EXISTS trg_ajuste_precio_no_update BEFORE UPDATE ON ajuste_precio BEGIN SELECT RAISE(ABORT, 'ajuste_precio es inmutable'); END;"))
    db_session.execute(text("CREATE TRIGGER IF NOT EXISTS trg_ajuste_precio_no_delete BEFORE DELETE ON ajuste_precio BEGIN SELECT RAISE(ABORT, 'ajuste_precio es inmutable'); END;"))
    db_session.execute(text("CREATE TRIGGER IF NOT EXISTS trg_pago_no_update BEFORE UPDATE ON pago BEGIN SELECT RAISE(ABORT, 'pago es inmutable'); END;"))
    db_session.execute(text("CREATE TRIGGER IF NOT EXISTS trg_pago_no_delete BEFORE DELETE ON pago BEGIN SELECT RAISE(ABORT, 'pago es inmutable'); END;"))
    db_session.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_pago_clave_idempotencia ON pago(clave_idempotencia) WHERE clave_idempotencia IS NOT NULL"))
    db_session.commit()


def test_validaciones_dinero_y_medios_pago(db_session, referencias_cobros):
    seed.sembrar_medios_pago(db_session)
    with pytest.raises(dinero.DineroError):
        dinero.validar_positivo(0)
    with pytest.raises(dinero.DineroError):
        dinero.validar_positivo(-1)
    with pytest.raises(dinero.DineroError):
        dinero.validar_positivo(1.5)  # type: ignore
    with pytest.raises(dinero.DineroError):
        dinero.a_centavos(1.5)  # type: ignore

    mp = db_session.execute(text("SELECT codigo FROM medio_pago ORDER BY codigo")).fetchall()
    codigos = [r[0] for r in mp]
    assert set(codigos) == {'EFECTIVO', 'DEBITO', 'TRANSFERENCIA', 'MERCADO_PAGO'}


def test_saldo_con_seña_parciales_ajuste_y_reverso(db_session, referencias_cobros):
    seed.sembrar_medios_pago(db_session)
    mp_id = db_session.execute(text("SELECT id FROM medio_pago WHERE codigo='EFECTIVO'")).scalar_one()
    cargo = models.Cargo(
        persona_id=referencias_cobros.persona_id,
        paciente_id=referencias_cobros.paciente_id,
        concepto='guarderia',
        total_inicial=3000000,
        origen=models.OrigenCargo.NORMAL,
        creado_por=referencias_cobros.usuario_id,
    )
    db_session.add(cargo)
    db_session.commit()
    db_session.refresh(cargo)

    # seña 1.000.000
    sena = models.Pago(cargo_id=cargo.id, monto=1000000, tipo=models.TipoPago.PAGO, medio_pago_id=mp_id, es_sena=True, fecha=date(2026, 1, 1), usuario_id=referencias_cobros.usuario_id)
    db_session.add(sena)
    # pago 1.500.000
    pago = models.Pago(cargo_id=cargo.id, monto=1500000, tipo=models.TipoPago.PAGO, medio_pago_id=mp_id, es_sena=False, fecha=date(2026, 1, 2), usuario_id=referencias_cobros.usuario_id)
    db_session.add(pago)
    db_session.commit()

    assert repository.total_vigente(db_session, cargo.id) == 3000000
    assert repository.total_pagado(db_session, cargo.id) == 2500000
    assert repository.saldo(db_session, cargo.id) == 500000

    # ajuste a 2.800.000
    ajuste = models.AjustePrecio(cargo_id=cargo.id, precio_anterior=3000000, precio_nuevo=2800000, motivo='descuento', usuario_id=referencias_cobros.usuario_id)
    db_session.add(ajuste)
    db_session.commit()
    assert repository.total_vigente(db_session, cargo.id) == 2800000
    assert repository.saldo(db_session, cargo.id) == 300000

    # reverso del pago de 1.500.000
    reverso = models.Pago(cargo_id=cargo.id, monto=1500000, tipo=models.TipoPago.REVERSO, pago_revertido_id=pago.id, medio_pago_id=mp_id, es_sena=False, fecha=date(2026, 1, 3), usuario_id=referencias_cobros.usuario_id)
    db_session.add(reverso)
    db_session.commit()
    assert repository.total_pagado(db_session, cargo.id) == 1000000
    assert repository.saldo(db_session, cargo.id) == 1800000


def test_reverso_mismo_cargo_y_clave_idempotencia(db_session, referencias_cobros):
    _crear_triggers(db_session)
    seed.sembrar_medios_pago(db_session)
    mp_id = db_session.execute(text("SELECT id FROM medio_pago WHERE codigo='EFECTIVO'")).scalar_one()
    cargo1 = models.Cargo(persona_id=referencias_cobros.persona_id, concepto='a', total_inicial=100000, creado_por=referencias_cobros.usuario_id)
    cargo2 = models.Cargo(persona_id=referencias_cobros.persona_id, concepto='b', total_inicial=100000, creado_por=referencias_cobros.usuario_id)
    db_session.add_all([cargo1, cargo2])
    db_session.commit()
    db_session.refresh(cargo1)
    db_session.refresh(cargo2)

    p1 = models.Pago(cargo_id=cargo1.id, monto=50000, tipo=models.TipoPago.PAGO, medio_pago_id=mp_id, fecha=date(2026, 1, 1), usuario_id=referencias_cobros.usuario_id)
    db_session.add(p1)
    db_session.commit()

    # reverso apunta a otro cargo debe fallar
    p_bad = models.Pago(cargo_id=cargo2.id, monto=50000, tipo=models.TipoPago.REVERSO, pago_revertido_id=p1.id, medio_pago_id=mp_id, fecha=date(2026, 1, 2), usuario_id=referencias_cobros.usuario_id)
    db_session.add(p_bad)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # clave_idempotencia repetida falla
    p2 = models.Pago(cargo_id=cargo1.id, monto=20000, tipo=models.TipoPago.PAGO, medio_pago_id=mp_id, fecha=date(2026, 1, 3), usuario_id=referencias_cobros.usuario_id, clave_idempotencia='abc')
    db_session.add(p2)
    db_session.commit()
    p3 = models.Pago(cargo_id=cargo1.id, monto=30000, tipo=models.TipoPago.PAGO, medio_pago_id=mp_id, fecha=date(2026, 1, 4), usuario_id=referencias_cobros.usuario_id, clave_idempotencia='abc')
    db_session.add(p3)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
    # dos pagos con clave nula conviven
    p4 = models.Pago(cargo_id=cargo1.id, monto=10000, tipo=models.TipoPago.PAGO, medio_pago_id=mp_id, fecha=date(2026, 1, 5), usuario_id=referencias_cobros.usuario_id)
    p5 = models.Pago(cargo_id=cargo1.id, monto=15000, tipo=models.TipoPago.PAGO, medio_pago_id=mp_id, fecha=date(2026, 1, 6), usuario_id=referencias_cobros.usuario_id)
    db_session.add_all([p4, p5])
    db_session.commit()


def test_total_vigente_con_dos_ajustes_encadenados(db_session, referencias_cobros):
    cargo = models.Cargo(
        persona_id=referencias_cobros.persona_id,
        concepto='x',
        total_inicial=100000,
        creado_por=referencias_cobros.usuario_id,
    )
    db_session.add(cargo)
    db_session.commit()
    db_session.refresh(cargo)
    db_session.add(models.AjustePrecio(cargo_id=cargo.id, precio_anterior=100000, precio_nuevo=80000, motivo='m1', usuario_id=referencias_cobros.usuario_id))
    db_session.commit()
    db_session.add(models.AjustePrecio(cargo_id=cargo.id, precio_anterior=80000, precio_nuevo=70000, motivo='m2', usuario_id=referencias_cobros.usuario_id))
    db_session.commit()
    assert repository.total_vigente(db_session, cargo.id) == 70000
