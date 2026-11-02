"""Egresos operativos mínimos e índices del panel financiero (T-38 / T-46).

Revision ID: 0019
Revises: 0018
Create Date: 2026-11-02
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0019"
down_revision: Union[str, Sequence[str], None] = "0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "categoria_egreso",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=80), nullable=False),
        sa.Column("nombre_normalizado", sa.String(length=80), nullable=False),
        sa.Column("activa", sa.Boolean(), server_default="1", nullable=False),
        sa.CheckConstraint(
            "trim(nombre) <> ''", name="ck_categoria_egreso_nombre_no_vacio"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_categoria_egreso")),
        sa.UniqueConstraint(
            "nombre_normalizado", name=op.f("uq_categoria_egreso_nombre_normalizado")
        ),
    )

    op.create_table(
        "egreso",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("monto_centavos", sa.Integer(), nullable=False),
        sa.Column("categoria_id", sa.Integer(), nullable=False),
        sa.Column("descripcion", sa.String(length=255), nullable=False),
        sa.Column("medio_pago_id", sa.Integer(), nullable=True),
        sa.Column("registrado_por", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("anulado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("anulado_por", sa.Integer(), nullable=True),
        sa.Column("motivo_anulacion", sa.String(length=255), nullable=True),
        sa.CheckConstraint("monto_centavos > 0", name="ck_egreso_monto_positivo"),
        sa.CheckConstraint(
            "typeof(monto_centavos) = 'integer'", name="ck_egreso_monto_entero"
        ),
        sa.ForeignKeyConstraint(
            ["categoria_id"], ["categoria_egreso.id"], name="fk_egreso_categoria"
        ),
        sa.ForeignKeyConstraint(
            ["medio_pago_id"], ["medio_pago.id"], name="fk_egreso_medio_pago"
        ),
        sa.ForeignKeyConstraint(["registrado_por"], ["usuario.id"], name="fk_egreso_usuario"),
        sa.ForeignKeyConstraint(
            ["anulado_por"], ["usuario.id"], name="fk_egreso_anulado_por_usuario"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_egreso")),
    )
    op.create_index("ix_egreso_fecha", "egreso", ["fecha"])
    op.create_index("ix_egreso_categoria_id", "egreso", ["categoria_id"])

    # Índices de apoyo para las consultas agregadas del panel.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_gasto_externo_fecha ON gasto_externo (fecha)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_pago_fecha ON pago (fecha)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_gasto_externo_fecha")
    op.drop_index("ix_egreso_categoria_id", table_name="egreso")
    op.drop_index("ix_egreso_fecha", table_name="egreso")
    op.drop_table("egreso")
    op.drop_table("categoria_egreso")
