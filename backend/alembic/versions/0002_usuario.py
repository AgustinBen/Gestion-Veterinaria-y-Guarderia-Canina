"""usuario

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-26 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'usuario',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column(
            'rol',
            sa.Enum(
                'DUENIO',
                'PERSONAL',
                'VETERINARIO',
                name='rol_usuario',
                native_enum=False,
                length=20,
                create_constraint=False,
            ),
            nullable=False,
        ),
        sa.Column('activo', sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column('empleado_id', sa.Integer(), nullable=True),
        sa.Column(
            'creado_en',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_usuario')),
    )
    with op.batch_alter_table('usuario', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_usuario_username'), ['username'], unique=True
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('usuario', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_usuario_username'))

    op.drop_table('usuario')
