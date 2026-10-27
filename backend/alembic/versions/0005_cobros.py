"""cobros

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-27 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0005'
down_revision: Union[str, Sequence[str], None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'medio_pago',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('codigo', sa.String(length=30), nullable=False),
        sa.Column('nombre', sa.String(length=60), nullable=False),
        sa.Column('activo', sa.Boolean(), server_default='1', nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_medio_pago')),
        sa.UniqueConstraint('codigo', name=op.f('uq_medio_pago_codigo')),
    )
    op.bulk_insert(
        sa.table('medio_pago', sa.column('codigo', sa.String()), sa.column('nombre', sa.String()), sa.column('activo', sa.Boolean())),
        [
            {'codigo': 'EFECTIVO', 'nombre': 'Efectivo', 'activo': True},
            {'codigo': 'DEBITO', 'nombre': 'Débito', 'activo': True},
            {'codigo': 'TRANSFERENCIA', 'nombre': 'Transferencia', 'activo': True},
            {'codigo': 'MERCADO_PAGO', 'nombre': 'Mercado Pago', 'activo': True},
        ],
    )

    op.create_table(
        'cargo',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('persona_id', sa.Integer(), nullable=False),
        sa.Column('paciente_id', sa.Integer(), nullable=True),
        sa.Column('concepto', sa.String(length=255), nullable=False),
        sa.Column('total_inicial', sa.Integer(), nullable=False),
        sa.Column('origen', sa.Enum('NORMAL', 'MIGRACION', name='origen_cargo', native_enum=False, length=20, create_constraint=False), nullable=False, server_default='NORMAL'),
        sa.Column('texto_original', sa.String(length=500), nullable=True),
        sa.Column('referencia_tipo', sa.String(length=50), nullable=True),
        sa.Column('referencia_id', sa.Integer(), nullable=True),
        sa.Column('creado_por', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.CheckConstraint('total_inicial > 0', name=op.f('ck_cargo_total_inicial_positivo')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_cargo')),
    )
    op.create_index('ix_cargo_persona_id', 'cargo', ['persona_id'], unique=False)
    op.create_index('ix_cargo_paciente_id', 'cargo', ['paciente_id'], unique=False)

    op.create_table(
        'ajuste_precio',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cargo_id', sa.Integer(), nullable=False),
        sa.Column('precio_anterior', sa.Integer(), nullable=False),
        sa.Column('precio_nuevo', sa.Integer(), nullable=False),
        sa.Column('motivo', sa.String(length=255), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.CheckConstraint('precio_nuevo > 0', name=op.f('ck_ajuste_precio_nuevo_positivo')),
        sa.ForeignKeyConstraint(['cargo_id'], ['cargo.id'], name=op.f('fk_ajuste_precio_cargo_id_cargo')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_ajuste_precio')),
    )
    op.create_index('ix_ajuste_precio_cargo_id', 'ajuste_precio', ['cargo_id'], unique=False)

    op.create_table(
        'pago',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cargo_id', sa.Integer(), nullable=False),
        sa.Column('monto', sa.Integer(), nullable=False),
        sa.Column('tipo', sa.Enum('PAGO', 'REVERSO', name='tipo_pago', native_enum=False, length=20, create_constraint=False), nullable=False),
        sa.Column('pago_revertido_id', sa.Integer(), nullable=True),
        sa.Column('medio_pago_id', sa.Integer(), nullable=False),
        sa.Column('es_sena', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('fecha', sa.Date(), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=False),
        sa.Column('empleado_id', sa.Integer(), nullable=True),
        sa.Column('clave_idempotencia', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.CheckConstraint('monto > 0', name=op.f('ck_pago_monto_positivo')),
        sa.ForeignKeyConstraint(['cargo_id'], ['cargo.id'], name=op.f('fk_pago_cargo_id_cargo')),
        sa.ForeignKeyConstraint(['pago_revertido_id'], ['pago.id'], name=op.f('fk_pago_pago_revertido_id_pago')),
        sa.ForeignKeyConstraint(['medio_pago_id'], ['medio_pago.id'], name=op.f('fk_pago_medio_pago_id_medio_pago')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_pago')),
    )
    op.create_index('ix_pago_cargo_id', 'pago', ['cargo_id'], unique=False)
    op.create_index('ix_pago_fecha', 'pago', ['fecha'], unique=False)
    op.execute("CREATE UNIQUE INDEX uq_pago_clave_idempotencia ON pago(clave_idempotencia) WHERE clave_idempotencia IS NOT NULL")

    op.create_table(
        'servicio_prestado',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cargo_id', sa.Integer(), nullable=False),
        sa.Column('empleado_id', sa.Integer(), nullable=False),
        sa.Column('descripcion', sa.String(length=255), nullable=False),
        sa.Column('fecha', sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(['cargo_id'], ['cargo.id'], name=op.f('fk_servicio_prestado_cargo_id_cargo')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_servicio_prestado')),
    )
    op.create_index('ix_servicio_prestado_cargo_id', 'servicio_prestado', ['cargo_id'], unique=False)

    op.create_table(
        'gasto_externo',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('empleado_id', sa.Integer(), nullable=False),
        sa.Column('descripcion', sa.String(length=255), nullable=False),
        sa.Column('monto', sa.Integer(), nullable=False),
        sa.Column('fecha', sa.Date(), nullable=False),
        sa.Column('cargo_id', sa.Integer(), nullable=True),
        sa.Column('pago_id', sa.Integer(), nullable=True),
        sa.Column('registrado_por', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['cargo_id'], ['cargo.id'], name=op.f('fk_gasto_externo_cargo_id_cargo')),
        sa.ForeignKeyConstraint(['pago_id'], ['pago.id'], name=op.f('fk_gasto_externo_pago_id_pago')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_gasto_externo')),
    )
    op.create_index('ix_gasto_externo_cargo_id', 'gasto_externo', ['cargo_id'], unique=False)
    op.create_index('ix_gasto_externo_pago_id', 'gasto_externo', ['pago_id'], unique=False)

    # Triggers de inmutabilidad
    op.execute("CREATE TRIGGER trg_cargo_no_update BEFORE UPDATE ON cargo BEGIN SELECT RAISE(ABORT, 'cargo es inmutable'); END;")
    op.execute("CREATE TRIGGER trg_cargo_no_delete BEFORE DELETE ON cargo BEGIN SELECT RAISE(ABORT, 'cargo es inmutable'); END;")
    op.execute("CREATE TRIGGER trg_ajuste_precio_no_update BEFORE UPDATE ON ajuste_precio BEGIN SELECT RAISE(ABORT, 'ajuste_precio es inmutable'); END;")
    op.execute("CREATE TRIGGER trg_ajuste_precio_no_delete BEFORE DELETE ON ajuste_precio BEGIN SELECT RAISE(ABORT, 'ajuste_precio es inmutable'); END;")
    op.execute("CREATE TRIGGER trg_pago_no_update BEFORE UPDATE ON pago BEGIN SELECT RAISE(ABORT, 'pago es inmutable'); END;")
    op.execute("CREATE TRIGGER trg_pago_no_delete BEFORE DELETE ON pago BEGIN SELECT RAISE(ABORT, 'pago es inmutable'); END;")


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_pago_no_delete")
    op.execute("DROP TRIGGER IF EXISTS trg_pago_no_update")
    op.execute("DROP TRIGGER IF EXISTS trg_ajuste_precio_no_delete")
    op.execute("DROP TRIGGER IF EXISTS trg_ajuste_precio_no_update")
    op.execute("DROP TRIGGER IF EXISTS trg_cargo_no_delete")
    op.execute("DROP TRIGGER IF EXISTS trg_cargo_no_update")

    op.drop_index('ix_gasto_externo_pago_id', table_name='gasto_externo')
    op.drop_index('ix_gasto_externo_cargo_id', table_name='gasto_externo')
    op.drop_table('gasto_externo')

    op.drop_index('ix_servicio_prestado_cargo_id', table_name='servicio_prestado')
    op.drop_table('servicio_prestado')

    op.drop_index('uq_pago_clave_idempotencia', table_name='pago')
    op.drop_index('ix_pago_fecha', table_name='pago')
    op.drop_index('ix_pago_cargo_id', table_name='pago')
    op.drop_table('pago')

    op.drop_index('ix_ajuste_precio_cargo_id', table_name='ajuste_precio')
    op.drop_table('ajuste_precio')

    op.drop_index('ix_cargo_paciente_id', table_name='cargo')
    op.drop_index('ix_cargo_persona_id', table_name='cargo')
    op.drop_table('cargo')

    op.drop_table('medio_pago')
