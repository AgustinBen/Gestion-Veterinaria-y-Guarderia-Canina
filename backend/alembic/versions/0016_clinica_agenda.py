"""Crear agenda clínica y turnos de personal.

Revision ID: 0016
Revises: 0015
Create Date: 2026-11-01
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0016"
down_revision: Union[str, Sequence[str], None] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

franja_turno_personal = sa.Enum(
    "MANANA",
    "TARDE",
    "NOCHE",
    name="franja_turno_personal",
    native_enum=False,
    length=10,
    create_constraint=True,
    validate_strings=True,
)


def upgrade() -> None:
    op.create_table(
        "horario_atencion",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dia_semana", sa.Integer(), nullable=False),
        sa.Column("hora_desde", sa.Time(), nullable=False),
        sa.Column("hora_hasta", sa.Time(), nullable=False),
        sa.CheckConstraint(
            "dia_semana >= 0 AND dia_semana <= 6",
            name="ck_horario_dia_semana",
        ),
        sa.CheckConstraint("hora_desde < hora_hasta", name="ck_horario_rango"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_horario_atencion_dia",
        "horario_atencion",
        ["dia_semana", "hora_desde"],
    )
    op.create_table(
        "turno_personal_def",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("turno", franja_turno_personal, nullable=False),
        sa.Column("hora_desde", sa.Time(), nullable=False),
        sa.Column("hora_hasta", sa.Time(), nullable=False),
        sa.CheckConstraint(
            "hora_desde != hora_hasta",
            name="ck_turno_personal_def_rango",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("turno", name="uq_turno_personal_def_turno"),
    )
    op.create_table(
        "turno_personal",
        sa.Column("empleado_id", sa.Integer(), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("turno", franja_turno_personal, nullable=False),
        sa.ForeignKeyConstraint(["empleado_id"], ["empleado.persona_id"]),
        sa.PrimaryKeyConstraint("empleado_id", "fecha", "turno"),
    )
    op.create_index(
        "ix_turno_personal_fecha_turno",
        "turno_personal",
        ["fecha", "turno"],
    )
    op.create_table(
        "turno",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("paciente_id", sa.Integer(), nullable=False),
        sa.Column(
            "tipo",
            sa.Enum(
                "CONSULTA",
                "VACUNA",
                "CIRUGIA",
                "ESTUDIO",
                "CONTROL",
                name="tipo_turno_medico",
                native_enum=False,
                length=20,
                create_constraint=True,
                validate_strings=True,
            ),
            nullable=False,
        ),
        sa.Column("veterinario_empleado_id", sa.Integer(), nullable=False),
        sa.Column("inicio", sa.DateTime(), nullable=False),
        sa.Column("fin", sa.DateTime(), nullable=False),
        sa.Column(
            "estado",
            sa.Enum(
                "PROGRAMADO",
                "PENDIENTE_EXTERNO",
                "CONFIRMADO",
                "ATENDIDO",
                "CANCELADO",
                "AUSENTE",
                name="estado_turno",
                native_enum=False,
                length=20,
                create_constraint=True,
                validate_strings=True,
            ),
            server_default="PROGRAMADO",
            nullable=False,
        ),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column("atencion_id", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint("inicio < fin", name="ck_turno_rango"),
        sa.ForeignKeyConstraint(["atencion_id"], ["atencion.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["usuario.id"]),
        sa.ForeignKeyConstraint(["paciente_id"], ["paciente.id"]),
        sa.ForeignKeyConstraint(
            ["veterinario_empleado_id"],
            ["empleado.persona_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_turno_veterinario_inicio",
        "turno",
        ["veterinario_empleado_id", "inicio"],
    )
    op.create_index(
        "ix_turno_paciente_inicio",
        "turno",
        ["paciente_id", "inicio"],
    )


def downgrade() -> None:
    op.drop_index("ix_turno_paciente_inicio", table_name="turno")
    op.drop_index("ix_turno_veterinario_inicio", table_name="turno")
    op.drop_table("turno")
    op.drop_index("ix_turno_personal_fecha_turno", table_name="turno_personal")
    op.drop_table("turno_personal")
    op.drop_table("turno_personal_def")
    op.drop_index("ix_horario_atencion_dia", table_name="horario_atencion")
    op.drop_table("horario_atencion")
