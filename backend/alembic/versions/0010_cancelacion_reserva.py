"""Auditar cancelaciones de reservas y permitir cerrar cargos en cero.

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-01
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0010"
down_revision: Union[str, Sequence[str], None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cancelacion_reserva",
        sa.Column("reserva_id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("clave_idempotencia", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["reserva_id"], ["reserva.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"]),
        sa.PrimaryKeyConstraint("reserva_id"),
        sa.UniqueConstraint(
            "clave_idempotencia",
            name="uq_cancelacion_clave_idempotencia",
        ),
    )

    with op.batch_alter_table("ajuste_precio") as batch_op:
        batch_op.drop_constraint(
            op.f("ck_ajuste_precio_nuevo_positivo"),
            type_="check",
        )
        batch_op.create_check_constraint(
            op.f("ck_ajuste_precio_nuevo_no_negativo"),
            "precio_nuevo >= 0",
        )

    op.execute(
        "CREATE TRIGGER trg_ajuste_precio_no_update "
        "BEFORE UPDATE ON ajuste_precio "
        "BEGIN SELECT RAISE(ABORT, 'ajuste_precio es inmutable'); END;"
    )
    op.execute(
        "CREATE TRIGGER trg_ajuste_precio_no_delete "
        "BEFORE DELETE ON ajuste_precio "
        "BEGIN SELECT RAISE(ABORT, 'ajuste_precio es inmutable'); END;"
    )
    op.execute(
        "CREATE TRIGGER trg_cancelacion_reserva_no_update "
        "BEFORE UPDATE ON cancelacion_reserva "
        "BEGIN SELECT RAISE(ABORT, 'cancelacion_reserva es inmutable'); END;"
    )
    op.execute(
        "CREATE TRIGGER trg_cancelacion_reserva_no_delete "
        "BEFORE DELETE ON cancelacion_reserva "
        "BEGIN SELECT RAISE(ABORT, 'cancelacion_reserva es inmutable'); END;"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_cancelacion_reserva_no_update")
    op.execute("DROP TRIGGER trg_cancelacion_reserva_no_delete")
    op.execute("DROP TRIGGER trg_ajuste_precio_no_update")
    op.execute("DROP TRIGGER trg_ajuste_precio_no_delete")
    with op.batch_alter_table("ajuste_precio") as batch_op:
        batch_op.drop_constraint(
            op.f("ck_ajuste_precio_nuevo_no_negativo"),
            type_="check",
        )
        batch_op.create_check_constraint(
            op.f("ck_ajuste_precio_nuevo_positivo"),
            "precio_nuevo > 0",
        )
    op.drop_table("cancelacion_reserva")
    op.execute(
        "CREATE TRIGGER trg_ajuste_precio_no_update "
        "BEFORE UPDATE ON ajuste_precio "
        "BEGIN SELECT RAISE(ABORT, 'ajuste_precio es inmutable'); END;"
    )
    op.execute(
        "CREATE TRIGGER trg_ajuste_precio_no_delete "
        "BEFORE DELETE ON ajuste_precio "
        "BEGIN SELECT RAISE(ABORT, 'ajuste_precio es inmutable'); END;"
    )
