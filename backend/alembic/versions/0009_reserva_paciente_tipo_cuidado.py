"""Guardar el detalle de cuidados especiales por paciente de la reserva.

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-31
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0009"
down_revision: Union[str, Sequence[str], None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "reserva_paciente",
        sa.Column("tipo_cuidado", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("reserva_paciente", "tipo_cuidado")
