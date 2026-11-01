"""Crear historia clínica estructurada y libreta de vacunas.

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-01
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0012"
down_revision: Union[str, Sequence[str], None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "atencion",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("paciente_id", sa.Integer(), nullable=False),
        sa.Column(
            "tipo",
            sa.Enum(
                "CONSULTA",
                "VACUNA",
                "CIRUGIA",
                "TRATAMIENTO",
                "ESTUDIO",
                name="tipo_atencion",
                native_enum=False,
                length=20,
                create_constraint=True,
                validate_strings=True,
            ),
            nullable=False,
        ),
        sa.Column("fecha_hora", sa.DateTime(timezone=True), nullable=False),
        sa.Column("veterinario_empleado_id", sa.Integer(), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column("diagnostico", sa.Text(), nullable=True),
        sa.Column("tratamiento", sa.Text(), nullable=True),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("cirujano_externo_id", sa.Integer(), nullable=True),
        sa.Column("cargo_id", sa.Integer(), nullable=True),
        sa.Column(
            "origen",
            sa.Enum(
                "NORMAL",
                "MIGRACION",
                name="origen_atencion",
                native_enum=False,
                length=20,
                create_constraint=True,
                validate_strings=True,
            ),
            server_default="NORMAL",
            nullable=False,
        ),
        sa.Column("texto_original", sa.Text(), nullable=True),
        sa.Column("rectifica_a_id", sa.Integer(), nullable=True),
        sa.Column("rectificada", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "tipo != 'CIRUGIA' OR cirujano_externo_id IS NOT NULL",
            name="ck_atencion_cirugia_cirujano",
        ),
        sa.CheckConstraint(
            "tipo = 'CIRUGIA' OR cirujano_externo_id IS NULL",
            name="ck_atencion_sin_cirujano_no_cirugia",
        ),
        sa.ForeignKeyConstraint(["cargo_id"], ["cargo.id"]),
        sa.ForeignKeyConstraint(["cirujano_externo_id"], ["empleado.persona_id"]),
        sa.ForeignKeyConstraint(["created_by"], ["usuario.id"]),
        sa.ForeignKeyConstraint(["paciente_id"], ["paciente.id"]),
        sa.ForeignKeyConstraint(["rectifica_a_id"], ["atencion.id"]),
        sa.ForeignKeyConstraint(
            ["veterinario_empleado_id"], ["empleado.persona_id"]
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_atencion_paciente_fecha",
        "atencion",
        ["paciente_id", "fecha_hora", "id"],
    )
    op.create_table(
        "vacuna_aplicada",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("atencion_id", sa.Integer(), nullable=False),
        sa.Column("nombre_vacuna", sa.String(length=100), nullable=False),
        sa.Column("lote", sa.String(length=100), nullable=True),
        sa.Column("fecha_aplicacion", sa.Date(), nullable=False),
        sa.Column("proxima_dosis", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(["atencion_id"], ["atencion.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("atencion_id", name="uq_vacuna_aplicada_atencion"),
    )
    op.execute(
        "CREATE TRIGGER trg_atencion_no_update "
        "BEFORE UPDATE ON atencion "
        "WHEN NOT ("
        "OLD.rectificada = 0 AND NEW.rectificada = 1 "
        "AND OLD.id IS NEW.id "
        "AND OLD.paciente_id IS NEW.paciente_id "
        "AND OLD.tipo IS NEW.tipo "
        "AND OLD.fecha_hora IS NEW.fecha_hora "
        "AND OLD.veterinario_empleado_id IS NEW.veterinario_empleado_id "
        "AND OLD.motivo IS NEW.motivo "
        "AND OLD.diagnostico IS NEW.diagnostico "
        "AND OLD.tratamiento IS NEW.tratamiento "
        "AND OLD.observaciones IS NEW.observaciones "
        "AND OLD.cirujano_externo_id IS NEW.cirujano_externo_id "
        "AND OLD.cargo_id IS NEW.cargo_id "
        "AND OLD.origen IS NEW.origen "
        "AND OLD.texto_original IS NEW.texto_original "
        "AND OLD.rectifica_a_id IS NEW.rectifica_a_id "
        "AND OLD.created_by IS NEW.created_by "
        "AND OLD.created_at IS NEW.created_at"
        ") "
        "BEGIN SELECT RAISE(ABORT, 'atencion es inmutable salvo rectificacion'); END;"
    )
    op.execute(
        "CREATE TRIGGER trg_atencion_no_delete "
        "BEFORE DELETE ON atencion "
        "BEGIN SELECT RAISE(ABORT, 'atencion es inmutable'); END;"
    )
    op.execute(
        "CREATE TRIGGER trg_vacuna_aplicada_no_update "
        "BEFORE UPDATE ON vacuna_aplicada "
        "BEGIN SELECT RAISE(ABORT, 'vacuna_aplicada es inmutable'); END;"
    )
    op.execute(
        "CREATE TRIGGER trg_vacuna_aplicada_no_delete "
        "BEFORE DELETE ON vacuna_aplicada "
        "BEGIN SELECT RAISE(ABORT, 'vacuna_aplicada es inmutable'); END;"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_vacuna_aplicada_no_delete")
    op.execute("DROP TRIGGER trg_vacuna_aplicada_no_update")
    op.execute("DROP TRIGGER trg_atencion_no_delete")
    op.execute("DROP TRIGGER trg_atencion_no_update")
    op.drop_table("vacuna_aplicada")
    op.drop_index("ix_atencion_paciente_fecha", table_name="atencion")
    op.drop_table("atencion")
