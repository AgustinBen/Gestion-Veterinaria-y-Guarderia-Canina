"""parametros iniciales del padron

Revision ID: 0004
Revises: a3c601386540
Create Date: 2026-10-26 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0004'
down_revision: Union[str, Sequence[str], None] = 'a3c601386540'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_PARAMETROS = (
    (
        "padron.codigo_area_defecto",
        "11",
        "str",
        "Código de área que completa los teléfonos de 8 dígitos",
    ),
    (
        "padron.umbral_nombre_parecido",
        "0.85",
        "decimal",
        "Similitud mínima para avisar por nombre parecido (RN-06)",
    ),
)


def upgrade() -> None:
    """Siembra idempotente de los parámetros del módulo."""
    conn = op.get_bind()
    for clave, valor, tipo, descripcion in _PARAMETROS:
        conn.execute(
            sa.text(
                "INSERT INTO configuracion (clave, valor, tipo, modulo, descripcion) "
                "SELECT :clave, :valor, :tipo, 'padron', :descripcion "
                "WHERE NOT EXISTS ("
                "SELECT 1 FROM configuracion WHERE clave = :clave"
                ")"
            ),
            {
                "clave": clave,
                "valor": valor,
                "tipo": tipo,
                "descripcion": descripcion,
            },
        )


def downgrade() -> None:
    """Elimina los parámetros sembrados por esta migración."""
    op.execute(
        sa.text(
            "DELETE FROM configuracion WHERE clave IN ("
            "'padron.codigo_area_defecto', 'padron.umbral_nombre_parecido'"
            ")"
        )
    )
