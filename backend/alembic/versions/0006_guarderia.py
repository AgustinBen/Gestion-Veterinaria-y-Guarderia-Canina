"""modelo base de guardería

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-30 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: Union[str, Sequence[str], None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_FRANJA = sa.Enum(
    "DIA",
    "NOCHE",
    name="franja_guarderia",
    native_enum=False,
    length=5,
    create_constraint=True,
)


def upgrade() -> None:
    op.create_table(
        "reserva",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tutor_persona_id", sa.Integer(), nullable=False),
        sa.Column("desde_fecha", sa.Date(), nullable=False),
        sa.Column("desde_franja", _FRANJA, nullable=False),
        sa.Column("hasta_fecha", sa.Date(), nullable=False),
        sa.Column("hasta_franja", _FRANJA, nullable=False),
        sa.Column(
            "estado",
            sa.Enum(
                "PENDIENTE_SENA",
                "CONFIRMADA",
                "EN_CURSO",
                "FINALIZADA",
                "CANCELADA",
                "AUSENTE",
                name="estado_reserva",
                native_enum=False,
                length=20,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("cargo_id", sa.Integer(), nullable=True),
        sa.Column("clave_idempotencia", sa.String(length=64), nullable=True),
        sa.Column("creado_por", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "desde_fecha < hasta_fecha OR "
            "(desde_fecha = hasta_fecha AND desde_franja <= hasta_franja)",
            name=op.f("ck_reserva_tramo_valido"),
        ),
        sa.ForeignKeyConstraint(
            ["tutor_persona_id"],
            ["persona.id"],
            name=op.f("fk_reserva_tutor_persona_id_persona"),
        ),
        sa.ForeignKeyConstraint(
            ["cargo_id"], ["cargo.id"], name=op.f("fk_reserva_cargo_id_cargo")
        ),
        sa.ForeignKeyConstraint(
            ["creado_por"], ["usuario.id"], name=op.f("fk_reserva_creado_por_usuario")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reserva")),
        sa.UniqueConstraint(
            "clave_idempotencia",
            name=op.f("uq_reserva_clave_idempotencia"),
        ),
    )

    op.create_table(
        "reserva_paciente",
        sa.Column("reserva_id", sa.Integer(), nullable=False),
        sa.Column("paciente_id", sa.Integer(), nullable=False),
        sa.Column("cuidados_extras", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["reserva_id"], ["reserva.id"], name=op.f("fk_reserva_paciente_reserva_id_reserva")
        ),
        sa.ForeignKeyConstraint(
            ["paciente_id"],
            ["paciente.id"],
            name=op.f("fk_reserva_paciente_paciente_id_paciente"),
        ),
        sa.PrimaryKeyConstraint(
            "reserva_id", "paciente_id", name=op.f("pk_reserva_paciente")
        ),
    )

    op.create_table(
        "ocupacion",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("franja", _FRANJA, nullable=False),
        sa.Column("reserva_id", sa.Integer(), nullable=False),
        sa.Column("paciente_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["reserva_id"], ["reserva.id"], name=op.f("fk_ocupacion_reserva_id_reserva")
        ),
        sa.ForeignKeyConstraint(
            ["paciente_id"],
            ["paciente.id"],
            name=op.f("fk_ocupacion_paciente_id_paciente"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ocupacion")),
        sa.UniqueConstraint(
            "fecha",
            "franja",
            "paciente_id",
            name="uq_ocupacion_fecha_franja_paciente",
        ),
    )
    op.create_index(
        "ix_ocupacion_fecha_franja",
        "ocupacion",
        ["fecha", "franja"],
        unique=False,
    )

    op.create_table(
        "habilitacion_emergencia",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("franja", _FRANJA, nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("motivo", sa.String(length=500), nullable=False),
        sa.Column("clave_idempotencia", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "trim(motivo) != ''",
            name=op.f("ck_habilitacion_emergencia_motivo_no_vacio"),
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["usuario.id"],
            name=op.f("fk_habilitacion_emergencia_usuario_id_usuario"),
        ),
        sa.PrimaryKeyConstraint(
            "id", name=op.f("pk_habilitacion_emergencia")
        ),
        sa.UniqueConstraint(
            "clave_idempotencia",
            name=op.f("uq_habilitacion_emergencia_clave_idempotencia"),
        ),
    )

    op.execute(
        "CREATE TRIGGER trg_habilitacion_emergencia_no_update "
        "BEFORE UPDATE ON habilitacion_emergencia "
        "BEGIN SELECT RAISE(ABORT, 'habilitacion_emergencia es inmutable'); END;"
    )
    op.execute(
        "CREATE TRIGGER trg_habilitacion_emergencia_no_delete "
        "BEFORE DELETE ON habilitacion_emergencia "
        "BEGIN SELECT RAISE(ABORT, 'habilitacion_emergencia es inmutable'); END;"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_habilitacion_emergencia_no_delete")
    op.execute("DROP TRIGGER IF EXISTS trg_habilitacion_emergencia_no_update")
    op.drop_table("habilitacion_emergencia")
    op.drop_index("ix_ocupacion_fecha_franja", table_name="ocupacion")
    op.drop_table("ocupacion")
    op.drop_table("reserva_paciente")
    op.drop_table("reserva")
