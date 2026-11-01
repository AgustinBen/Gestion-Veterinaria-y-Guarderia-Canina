"""Registrar estudios clínicos y sus adjuntos.

Revision ID: 0015
Revises: 0014
Create Date: 2026-11-01
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0015"
down_revision: Union[str, Sequence[str], None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "estudio",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("paciente_id", sa.Integer(), nullable=False),
        sa.Column("atencion_id", sa.Integer(), nullable=True),
        sa.Column(
            "tipo",
            sa.Enum(
                "RADIOGRAFIA",
                "ECOGRAFIA",
                "ANALISIS",
                "OTRO",
                name="tipo_estudio",
                native_enum=False,
                length=20,
                create_constraint=True,
                validate_strings=True,
            ),
            nullable=False,
        ),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("realizado_por_empleado_id", sa.Integer(), nullable=False),
        sa.Column("cargo_id", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["atencion_id"], ["atencion.id"]),
        sa.ForeignKeyConstraint(["cargo_id"], ["cargo.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["usuario.id"]),
        sa.ForeignKeyConstraint(["paciente_id"], ["paciente.id"]),
        sa.ForeignKeyConstraint(["realizado_por_empleado_id"], ["empleado.persona_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_estudio_paciente_fecha",
        "estudio",
        ["paciente_id", "fecha", "id"],
    )
    op.create_table(
        "adjunto",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("estudio_id", sa.Integer(), nullable=False),
        sa.Column("nombre_original", sa.Text(), nullable=False),
        sa.Column("nombre_archivo", sa.String(length=64), nullable=False),
        sa.Column("tipo_mime", sa.String(length=100), nullable=False),
        sa.Column("tamano_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["created_by"], ["usuario.id"]),
        sa.ForeignKeyConstraint(["estudio_id"], ["estudio.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nombre_archivo"),
    )
    op.create_index("ix_adjunto_estudio_id", "adjunto", ["estudio_id"])


def downgrade() -> None:
    op.drop_index("ix_adjunto_estudio_id", table_name="adjunto")
    op.drop_table("adjunto")
    op.drop_index("ix_estudio_paciente_fecha", table_name="estudio")
    op.drop_table("estudio")
