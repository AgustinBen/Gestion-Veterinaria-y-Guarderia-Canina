"""motivo del reverso en pago

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-31
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: Union[str, Sequence[str], None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # add_column/drop_column directos: batch_alter_table recrearía `pago` y
    # perdería los triggers de inmutabilidad.
    op.add_column("pago", sa.Column("motivo", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("pago", "motivo")
