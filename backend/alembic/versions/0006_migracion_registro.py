"""migracion_registro

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-30 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0006'
down_revision: Union[str, Sequence[str], None] = '0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'migracion_registro',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('hoja', sa.String(length=60), nullable=False),
        sa.Column('fila', sa.Integer(), nullable=False),
        sa.Column('id_origen', sa.String(length=60), nullable=True),
        sa.Column('hash_fila', sa.String(length=64), nullable=False),
        sa.Column('texto_original', sa.Text(), nullable=False),
        sa.Column('entidad', sa.String(length=20), nullable=True),
        sa.Column('entidad_id', sa.Integer(), nullable=True),
        sa.Column('estado', sa.String(length=20), nullable=False),
        sa.Column('motivo', sa.String(length=255), nullable=True),
        sa.Column('origen_confirmacion', sa.String(length=40), nullable=True),
        sa.Column(
            'fecha',
            sa.DateTime(timezone=True),
            server_default=sa.text('(CURRENT_TIMESTAMP)'),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_migracion_registro')),
    )
    with op.batch_alter_table('migracion_registro') as batch_op:
        batch_op.create_unique_constraint(
            op.f('uq_migracion_registro_hoja_fila'), ['hoja', 'fila']
        )


def downgrade() -> None:
    with op.batch_alter_table('migracion_registro') as batch_op:
        batch_op.drop_constraint(
            op.f('uq_migracion_registro_hoja_fila'), type_='unique'
        )
    op.drop_table('migracion_registro')
