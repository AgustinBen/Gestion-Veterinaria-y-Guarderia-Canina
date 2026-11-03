"""Externo opcional en los gastos a externos (T-50).

Revision ID: 0021
Revises: 0020
Create Date: 2026-11-02
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0021"
down_revision: Union[str, Sequence[str], None] = "0020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("gasto_externo") as batch_op:
        batch_op.alter_column(
            "empleado_id", existing_type=sa.Integer(), nullable=True
        )


def downgrade() -> None:
    with op.batch_alter_table("gasto_externo") as batch_op:
        batch_op.alter_column(
            "empleado_id", existing_type=sa.Integer(), nullable=False
        )
