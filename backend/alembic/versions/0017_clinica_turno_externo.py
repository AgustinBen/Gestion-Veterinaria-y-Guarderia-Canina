"""Agregar veterinario externo y su historial a los turnos de cirugía.

Revision ID: 0017
Revises: 0016
Create Date: 2026-11-01
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0017"
down_revision: Union[str, Sequence[str], None] = "0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

tipo_evento_externo = sa.Enum(
    "CONTACTADO",
    "CONFIRMADO",
    "RECHAZADO",
    "REEMPLAZADO",
    name="tipo_evento_externo",
    native_enum=False,
    length=20,
    create_constraint=True,
    validate_strings=True,
)

medio_evento_externo = sa.Enum(
    "TELEFONO",
    "WHATSAPP",
    "PRESENCIAL",
    "OTRO",
    name="medio_evento_externo",
    native_enum=False,
    length=20,
    create_constraint=True,
    validate_strings=True,
)


def upgrade() -> None:
    with op.batch_alter_table("turno") as batch_op:
        batch_op.add_column(
            sa.Column("externo_actual_id", sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_turno_externo_actual_id_empleado",
            "empleado",
            ["externo_actual_id"],
            ["persona_id"],
        )

    op.create_table(
        "turno_externo_evento",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("turno_id", sa.Integer(), nullable=False),
        sa.Column("tipo", tipo_evento_externo, nullable=False),
        sa.Column("externo_empleado_id", sa.Integer(), nullable=False),
        sa.Column("medio", medio_evento_externo, nullable=True),
        sa.Column("nota", sa.Text(), nullable=True),
        sa.Column("costo_acordado_centavos", sa.Integer(), nullable=True),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "costo_acordado_centavos IS NULL OR ("
            "typeof(costo_acordado_centavos) = 'integer' "
            "AND costo_acordado_centavos > 0)",
            name="ck_turno_externo_evento_costo_positivo",
        ),
        sa.CheckConstraint(
            "costo_acordado_centavos IS NULL OR tipo = 'CONFIRMADO'",
            name="ck_turno_externo_evento_costo_solo_confirmado",
        ),
        sa.ForeignKeyConstraint(
            ["externo_empleado_id"], ["empleado.persona_id"]
        ),
        sa.ForeignKeyConstraint(["turno_id"], ["turno.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_turno_externo_evento_turno",
        "turno_externo_evento",
        ["turno_id", "created_at", "id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_turno_externo_evento_turno", table_name="turno_externo_evento"
    )
    op.drop_table("turno_externo_evento")
    with op.batch_alter_table("turno") as batch_op:
        batch_op.drop_constraint(
            "fk_turno_externo_actual_id_empleado", type_="foreignkey"
        )
        batch_op.drop_column("externo_actual_id")
