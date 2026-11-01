"""Anulación auditada de gastos a externos.

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-01
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0010"
down_revision: Union[str, Sequence[str], None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("gasto_externo") as batch_op:
        batch_op.add_column(
            sa.Column("anulado_en", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(sa.Column("anulado_por", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("motivo_anulacion", sa.String(255), nullable=True))
        batch_op.create_foreign_key(
            "fk_gasto_externo_anulado_por_usuario",
            "usuario",
            ["anulado_por"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("gasto_externo") as batch_op:
        batch_op.drop_constraint(
            "fk_gasto_externo_anulado_por_usuario", type_="foreignkey"
        )
        batch_op.drop_column("motivo_anulacion")
        batch_op.drop_column("anulado_por")
        batch_op.drop_column("anulado_en")
