"""Cupo máximo configurable para fechas individuales.

Revision ID: 0022
Revises: 0021
Create Date: 2026-11-03
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0022"
down_revision: Union[str, Sequence[str], None] = "0021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "configuracion_cupo_fecha",
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("cupo_maximo", sa.Integer(), nullable=False),
        sa.Column("actualizado_por", sa.String(length=100), nullable=False),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("cupo_maximo > 0", name="cupo_maximo_positivo"),
        sa.PrimaryKeyConstraint("fecha"),
    )


def downgrade() -> None:
    op.drop_table("configuracion_cupo_fecha")
