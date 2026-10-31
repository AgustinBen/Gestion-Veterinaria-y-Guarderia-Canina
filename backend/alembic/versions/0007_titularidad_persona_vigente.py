"""Evitar titularidades vigentes duplicadas por persona y paciente.

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-31
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: Union[str, Sequence[str], None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_titularidad_unica_persona_vigente",
        "titularidad",
        ["paciente_id", "persona_id"],
        unique=True,
        sqlite_where=sa.text("hasta IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_titularidad_unica_persona_vigente",
        table_name="titularidad",
    )
