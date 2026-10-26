"""Consultas de persistencia del módulo identidad."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.models import Configuracion
from app.modules.identidad.models import Usuario
from app.modules.identidad.permisos import Rol


def obtener_por_id(db: Session, usuario_id: int) -> Usuario | None:
    """Busca un usuario por su id."""
    return db.get(Usuario, usuario_id)


def obtener_por_username(db: Session, username: str) -> Usuario | None:
    """Busca un usuario por su username ya normalizado (minúsculas)."""
    stmt = select(Usuario).where(Usuario.username == username)
    return db.execute(stmt).scalar_one_or_none()


def listar_usuarios(db: Session) -> list[Usuario]:
    """Lista todos los usuarios, activos e inactivos, ordenados por id."""
    stmt = select(Usuario).order_by(Usuario.id)
    return list(db.execute(stmt).scalars())


def crear_usuario(
    db: Session,
    *,
    username: str,
    password_hash: str,
    rol: Rol,
    empleado_id: int | None = None,
) -> Usuario:
    """Agrega un usuario a la sesión. El commit lo hace el service."""
    usuario = Usuario(
        username=username,
        password_hash=password_hash,
        rol=rol,
        empleado_id=empleado_id,
    )
    db.add(usuario)
    return usuario


def contar_duenios_activos(db: Session, excluir_id: int | None = None) -> int:
    """Cuenta los usuarios con rol DUENIO y activo, opcionalmente excluyendo uno."""
    stmt = (
        select(func.count())
        .select_from(Usuario)
        .where(Usuario.rol == Rol.DUENIO, Usuario.activo.is_(True))
    )
    if excluir_id is not None:
        stmt = stmt.where(Usuario.id != excluir_id)
    return db.execute(stmt).scalar_one()


def listar_configuracion(db: Session) -> list[Configuracion]:
    """Lista los parámetros configurados, ordenados por clave."""
    stmt = select(Configuracion).order_by(Configuracion.clave)
    return list(db.execute(stmt).scalars())


def obtener_configuracion(db: Session, clave: str) -> Configuracion | None:
    """Busca un parámetro por clave."""
    stmt = select(Configuracion).where(Configuracion.clave == clave)
    return db.execute(stmt).scalar_one_or_none()
