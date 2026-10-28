from sqlalchemy import inspect


def test_introspeccion_sin_saldo_ni_deuda(engine_sqlite):
    inspector = inspect(engine_sqlite)
    tablas_cobros = [
        'cargo',
        'pago',
        'ajuste_precio',
        'medio_pago',
        'servicio_prestado',
        'gasto_externo',
    ]
    for tabla in tablas_cobros:
        columnas = {col['name'] for col in inspector.get_columns(tabla)}
        assert 'saldo' not in columnas
        assert 'deuda' not in columnas

    columnas_dinero = {
        'cargo': {'total_inicial'},
        'ajuste_precio': {'precio_anterior', 'precio_nuevo'},
        'pago': {'monto'},
        'gasto_externo': {'monto'},
    }
    for tabla, nombres_columnas in columnas_dinero.items():
        columnas = {
            col['name']: col
            for col in inspector.get_columns(tabla)
        }
        for nombre in nombres_columnas:
            assert columnas[nombre]['type'].__class__.__name__ == 'INTEGER'


def test_referencias_a_entidades_de_otros_modulos(engine_sqlite):
    inspector = inspect(engine_sqlite)
    esperadas = {
        'cargo': {
            (('persona_id',), 'persona', ('id',)),
            (('paciente_id',), 'paciente', ('id',)),
            (('creado_por',), 'usuario', ('id',)),
        },
        'ajuste_precio': {
            (('usuario_id',), 'usuario', ('id',)),
        },
        'pago': {
            (('usuario_id',), 'usuario', ('id',)),
            (('empleado_id',), 'empleado', ('persona_id',)),
            (('pago_revertido_id', 'cargo_id'), 'pago', ('id', 'cargo_id')),
        },
        'servicio_prestado': {
            (('empleado_id',), 'empleado', ('persona_id',)),
        },
        'gasto_externo': {
            (('empleado_id',), 'empleado', ('persona_id',)),
            (('registrado_por',), 'usuario', ('id',)),
        },
    }

    for tabla, fks_esperadas in esperadas.items():
        fks = {
            (
                tuple(fk['constrained_columns']),
                fk['referred_table'],
                tuple(fk['referred_columns']),
            )
            for fk in inspector.get_foreign_keys(tabla)
        }
        assert fks_esperadas <= fks
