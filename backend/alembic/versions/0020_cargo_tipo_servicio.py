"""Tipo de servicio en el cargo para los filtros del panel (T-44 / T-46).

Revision ID: 0020
Revises: 0019
Create Date: 2026-11-02
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0020"
down_revision: Union[str, Sequence[str], None] = "0019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TRIGGER_UPDATE = (
    "CREATE TRIGGER trg_cargo_no_update BEFORE UPDATE ON cargo "
    "WHEN NEW.id IS NOT OLD.id "
    "OR NEW.concepto IS NOT OLD.concepto "
    "OR NEW.total_inicial IS NOT OLD.total_inicial "
    "OR NEW.tipo_servicio IS NOT OLD.tipo_servicio "
    "OR NEW.origen IS NOT OLD.origen "
    "OR NEW.texto_original IS NOT OLD.texto_original "
    "OR NEW.referencia_tipo IS NOT OLD.referencia_tipo "
    "OR NEW.referencia_id IS NOT OLD.referencia_id "
    "OR NEW.creado_por IS NOT OLD.creado_por "
    "OR NEW.created_at IS NOT OLD.created_at "
    "BEGIN SELECT RAISE(ABORT, 'cargo es inmutable'); END;"
)

_TRIGGER_DELETE = (
    "CREATE TRIGGER trg_cargo_no_delete BEFORE DELETE ON cargo "
    "BEGIN SELECT RAISE(ABORT, 'cargo es inmutable'); END;"
)

_TRIGGER_UPDATE_ORIGINAL = (
    "CREATE TRIGGER trg_cargo_no_update BEFORE UPDATE ON cargo "
    "BEGIN SELECT RAISE(ABORT, 'cargo es inmutable'); END;"
)


def _recrear_triggers(update: str) -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_cargo_no_update")
    op.execute("DROP TRIGGER IF EXISTS trg_cargo_no_delete")
    op.execute(update)
    op.execute(_TRIGGER_DELETE)


def upgrade() -> None:
    # El batch de SQLite agrega la columna con un ALTER nativo: los triggers
    # de inmutabilidad siguen existiendo y bloquearían los UPDATE de abajo.
    with op.batch_alter_table("cargo") as batch_op:
        batch_op.add_column(
            sa.Column(
                "tipo_servicio",
                sa.String(length=20),
                server_default="OTRO",
                nullable=False,
            )
        )

    op.execute("DROP TRIGGER IF EXISTS trg_cargo_no_update")
    op.execute("DROP TRIGGER IF EXISTS trg_cargo_no_delete")

    op.execute(
        "UPDATE cargo SET tipo_servicio = 'GUARDERIA' "
        "WHERE referencia_tipo = 'RESERVA'"
    )
    op.execute(
        "UPDATE cargo SET tipo_servicio = 'MIGRACION' WHERE origen = 'MIGRACION'"
    )

    op.create_index("ix_cargo_tipo_servicio", "cargo", ["tipo_servicio"])
    _recrear_triggers(_TRIGGER_UPDATE)


def downgrade() -> None:
    op.drop_index("ix_cargo_tipo_servicio", table_name="cargo")
    with op.batch_alter_table("cargo") as batch_op:
        batch_op.drop_column("tipo_servicio")
    _recrear_triggers(_TRIGGER_UPDATE_ORIGINAL)
