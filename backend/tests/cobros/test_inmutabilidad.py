from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.modules.cobros import models, seed


def _crear_triggers(db_session):
    db_session.execute(text("CREATE TRIGGER IF NOT EXISTS trg_cargo_no_update BEFORE UPDATE ON cargo BEGIN SELECT RAISE(ABORT, 'cargo es inmutable'); END;"))
    db_session.execute(text("CREATE TRIGGER IF NOT EXISTS trg_cargo_no_delete BEFORE DELETE ON cargo BEGIN SELECT RAISE(ABORT, 'cargo es inmutable'); END;"))
    db_session.execute(text("CREATE TRIGGER IF NOT EXISTS trg_ajuste_precio_no_update BEFORE UPDATE ON ajuste_precio BEGIN SELECT RAISE(ABORT, 'ajuste_precio es inmutable'); END;"))
    db_session.execute(text("CREATE TRIGGER IF NOT EXISTS trg_ajuste_precio_no_delete BEFORE DELETE ON ajuste_precio BEGIN SELECT RAISE(ABORT, 'ajuste_precio es inmutable'); END;"))
    db_session.execute(text("CREATE TRIGGER IF NOT EXISTS trg_pago_no_update BEFORE UPDATE ON pago BEGIN SELECT RAISE(ABORT, 'pago es inmutable'); END;"))
    db_session.execute(text("CREATE TRIGGER IF NOT EXISTS trg_pago_no_delete BEFORE DELETE ON pago BEGIN SELECT RAISE(ABORT, 'pago es inmutable'); END;"))
    db_session.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_pago_clave_idempotencia ON pago(clave_idempotencia) WHERE clave_idempotencia IS NOT NULL"))
    db_session.commit()


def test_update_y_delete_bloqueados_por_trigger(db_session, referencias_cobros):
    _crear_triggers(db_session)
    seed.sembrar_medios_pago(db_session)
    mp = db_session.execute(text("SELECT id FROM medio_pago WHERE codigo='EFECTIVO'")).fetchone()
    medio_id = mp[0]
    cargo = models.Cargo(
        persona_id=referencias_cobros.persona_id,
        paciente_id=referencias_cobros.paciente_id,
        concepto='consulta',
        total_inicial=3000000,
        origen=models.OrigenCargo.NORMAL,
        creado_por=referencias_cobros.usuario_id,
    )
    db_session.add(cargo)
    db_session.commit()
    db_session.refresh(cargo)

    ajuste = models.AjustePrecio(cargo_id=cargo.id, precio_anterior=3000000, precio_nuevo=2800000, motivo='ajuste', usuario_id=referencias_cobros.usuario_id)
    db_session.add(ajuste)
    db_session.commit()

    pago = models.Pago(cargo_id=cargo.id, monto=1000000, tipo=models.TipoPago.PAGO, medio_pago_id=medio_id, es_sena=True, fecha=date(2026, 1, 1), usuario_id=referencias_cobros.usuario_id)
    db_session.add(pago)
    db_session.commit()
    db_session.refresh(pago)

    with pytest.raises(IntegrityError):
        db_session.execute(text("UPDATE cargo SET concepto='x' WHERE id=:id"), {"id": cargo.id})
        db_session.commit()
    db_session.rollback()

    with pytest.raises(IntegrityError):
        db_session.execute(text("DELETE FROM cargo WHERE id=:id"), {"id": cargo.id})
        db_session.commit()
    db_session.rollback()

    with pytest.raises(IntegrityError):
        db_session.execute(text("UPDATE ajuste_precio SET motivo='x' WHERE id=:id"), {"id": ajuste.id})
        db_session.commit()
    db_session.rollback()

    with pytest.raises(IntegrityError):
        db_session.execute(text("DELETE FROM ajuste_precio WHERE id=:id"), {"id": ajuste.id})
        db_session.commit()
    db_session.rollback()

    with pytest.raises(IntegrityError):
        db_session.execute(text("UPDATE pago SET monto=500 WHERE id=:id"), {"id": pago.id})
        db_session.commit()
    db_session.rollback()

    with pytest.raises(IntegrityError):
        db_session.execute(text("DELETE FROM pago WHERE id=:id"), {"id": pago.id})
        db_session.commit()
    db_session.rollback()
