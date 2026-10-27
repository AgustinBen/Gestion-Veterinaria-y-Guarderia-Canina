from sqlalchemy import inspect


def test_introspeccion_sin_saldo_ni_deuda(engine_sqlite):
    inspector = inspect(engine_sqlite)
    for tabla in ['cargo', 'pago', 'ajuste_precio', 'medio_pago', 'servicio_prestado', 'gasto_externo']:
        columnas = {col['name'] for col in inspector.get_columns(tabla)}
        assert 'saldo' not in columnas
        assert 'deuda' not in columnas

    for tabla in ['cargo', 'pago', 'ajuste_precio']:
        columnas = inspector.get_columns(tabla)
        for col in columnas:
            if 'monto' in col['name'] or 'total' in col['name'] or 'precio' in col['name']:
                assert col['type'].__class__.__name__ in ('INTEGER',)
    assert True
