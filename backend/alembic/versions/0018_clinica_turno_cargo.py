"""Vincular un turno con el cargo que se cobra al dueño de la mascota.

Revision ID: 0018
Revises: 0017
Create Date: 2026-11-02
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0018"
down_revision: Union[str, Sequence[str], None] = "0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("turno") as batch_op:
        batch_op.add_column(sa.Column("cargo_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_turno_cargo_id_cargo", "cargo", ["cargo_id"], ["id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("turno") as batch_op:
        batch_op.drop_constraint("fk_turno_cargo_id_cargo", type_="foreignkey")
        batch_op.drop_column("cargo_id")
