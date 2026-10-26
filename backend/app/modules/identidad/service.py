"""Reglas de negocio del módulo identidad."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import parametros
from app.core.config import get_settings
from app.modules.identidad import repository, security
from app.modules.identidad.models import USERNAME_MAX_LENGTH, Usuario
from app.modules.identidad.permisos import Rol
from app.modules.identidad.schemas import (
    ConfiguracionItem,
    ConfiguracionUpdate,
    LoginResponse,
    UsuarioActual,
    UsuarioActualizar,
    UsuarioCrear,
    UsuarioPublico,
)


class NoAutenticado(Exception):
    """Credenciales inválidas, token inválido/vencido o usuario inactivo."""


class CredencialesInvalidas(Exception):
    """Login rechazado; no se distingue el motivo."""


class UsernameDuplicado(Exception):
    """Ya existe un usuario con ese username."""


class UsuarioNoEncontrado(Exception):
    """No existe el usuario solicitado."""


class UsuarioExistenteNoDuenio(Exception):
    """El bootstrap encontró un username ocupado por otro rol."""


class DatosInvalidos(Exception):
    """Datos que no cumplen una regla de negocio."""


class OperacionNoPermitida(Exception):
    """La operación dejaría el sistema en un estado inválido."""


class ConfiguracionNoEncontrada(Exception):
    """No existe la clave de configuración solicitada."""


def _normalizar_username(username: str) -> str:
    normalizado = username.strip().lower()
    if not normalizado:
        raise DatosInvalidos("El username no puede estar vacío")
    if len(normalizado) > USERNAME_MAX_LENGTH:
        raise DatosInvalidos(
            f"El username no puede superar los {USERNAME_MAX_LENGTH} caracteres"
        )
    return normalizado


def _validar_password(password: str) -> None:
    minimo = get_settings().password_min_length
    if len(password) < minimo:
        raise DatosInvalidos(
            f"La contraseña debe tener al menos {minimo} caracteres"
        )


def usuario_actual(db: Session, token: str) -> UsuarioActual:
    """Resuelve el usuario autenticado consultando estado y rol en la base.

    La consulta a la base se hace en cada pedido: un usuario desactivado no
    sigue autenticado aunque su token siga vigente.
    """
    try:
        payload = security.decodificar_token(token)
    except security.TokenInvalido as exc:
        raise NoAutenticado("No autenticado") from exc

    usuario = repository.obtener_por_id(db, payload.usuario_id)
    if usuario is None or not usuario.activo:
        raise NoAutenticado("No autenticado")

    return UsuarioActual.model_validate(usuario)


def tiene_rol(usuario: UsuarioActual, *roles: Rol) -> bool:
    """Indica si el usuario tiene alguno de los roles. Sin roles: deniega."""
    return usuario.rol in roles


def login(db: Session, username: str, password: str) -> LoginResponse:
    """Autentica y emite un token. Todos los rechazos son iguales."""
    normalizado = username.strip().lower()
    usuario = repository.obtener_por_username(db, normalizado)

    if usuario is None or not security.verificar_password(
        usuario.password_hash, password
    ):
        raise CredencialesInvalidas("Credenciales inválidas")
    if not usuario.activo:
        raise CredencialesInvalidas("Credenciales inválidas")

    token = security.crear_token(usuario.id, usuario.rol)
    return LoginResponse(access_token=token, rol=usuario.rol)


def listar_usuarios(db: Session) -> list[UsuarioPublico]:
    """Lista usuarios activos e inactivos, sin datos sensibles."""
    return [
        UsuarioPublico.model_validate(usuario)
        for usuario in repository.listar_usuarios(db)
    ]


def crear_usuario(db: Session, datos: UsuarioCrear) -> UsuarioPublico:
    """Crea un usuario con username normalizado y contraseña hasheada."""
    username = _normalizar_username(datos.username)
    _validar_password(datos.password)

    if repository.obtener_por_username(db, username) is not None:
        raise UsernameDuplicado(username)

    usuario = repository.crear_usuario(
        db,
        username=username,
        password_hash=security.hash_password(datos.password),
        rol=datos.rol,
        empleado_id=datos.empleado_id,
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise UsernameDuplicado(username) from exc

    db.refresh(usuario)
    return UsuarioPublico.model_validate(usuario)


def actualizar_usuario(
    db: Session,
    usuario_id: int,
    datos: UsuarioActualizar,
    actor: UsuarioActual,
) -> UsuarioPublico:
    """Aplica cambios parciales respetando las reglas de Dueño activo."""
    usuario = repository.obtener_por_id(db, usuario_id)
    if usuario is None:
        raise UsuarioNoEncontrado(usuario_id)

    campos = datos.model_fields_set
    if not campos:
        raise DatosInvalidos("No hay campos para actualizar")

    nuevo_activo = usuario.activo
    if "activo" in campos:
        if datos.activo is None:
            raise DatosInvalidos("El campo activo no puede ser nulo")
        nuevo_activo = datos.activo

    nuevo_rol = usuario.rol
    if "rol" in campos:
        if datos.rol is None:
            raise DatosInvalidos("El campo rol no puede ser nulo")
        nuevo_rol = datos.rol

    password: str | None = None
    if "password" in campos:
        password = datos.password
        if password is None:
            raise DatosInvalidos("El campo password no puede ser nulo")
        _validar_password(password)

    if "activo" in campos and not nuevo_activo and usuario.id == actor.id:
        raise OperacionNoPermitida("No podés desactivar tu propio usuario")

    pierde_duenio = usuario.rol == Rol.DUENIO and (
        not nuevo_activo or nuevo_rol != Rol.DUENIO
    )
    if (
        usuario.activo
        and pierde_duenio
        and repository.contar_duenios_activos(db, excluir_id=usuario.id) == 0
    ):
        raise OperacionNoPermitida(
            "No se puede dejar el sistema sin un Dueño activo"
        )

    if "activo" in campos:
        usuario.activo = nuevo_activo
    if "rol" in campos:
        usuario.rol = nuevo_rol
    if password is not None:
        usuario.password_hash = security.hash_password(password)

    db.commit()
    db.refresh(usuario)
    return UsuarioPublico.model_validate(usuario)


def listar_configuracion(db: Session) -> list[ConfiguracionItem]:
    """Lista los parámetros con su valor crudo y su tipo."""
    return [
        ConfiguracionItem.model_validate(parametro)
        for parametro in repository.listar_configuracion(db)
    ]


def _convertir_valor_configuracion(
    valor: str | int | float | bool, tipo: str
) -> Any:
    if tipo == "int":
        if isinstance(valor, bool):
            raise DatosInvalidos("Se esperaba un número entero")
        if isinstance(valor, int):
            return valor
        if isinstance(valor, str) and valor.strip().isdigit():
            return int(valor.strip())
        raise DatosInvalidos("Se esperaba un número entero")

    if tipo == "decimal":
        if isinstance(valor, bool):
            raise DatosInvalidos("Se esperaba un número decimal")
        try:
            numero = Decimal(str(valor))
        except InvalidOperation as exc:
            raise DatosInvalidos("Se esperaba un número decimal") from exc
        if not numero.is_finite():
            raise DatosInvalidos("Se esperaba un número decimal finito")
        return numero

    if tipo == "bool":
        if isinstance(valor, bool):
            return valor
        if isinstance(valor, str):
            normalizado = valor.strip().lower()
            if normalizado == "true":
                return True
            if normalizado == "false":
                return False
        raise DatosInvalidos("Se esperaba un booleano true o false")

    if tipo == "str":
        if isinstance(valor, str):
            return valor
        raise DatosInvalidos("Se esperaba un texto")

    raise DatosInvalidos(f"Tipo de configuración inválido: {tipo}")


def actualizar_configuracion(
    db: Session,
    clave: str,
    datos: ConfiguracionUpdate,
    actor: UsuarioActual,
) -> ConfiguracionItem:
    """Actualiza un parámetro existente; nunca crea claves ni cambia el tipo."""
    actual = repository.obtener_configuracion(db, clave)
    if actual is None:
        raise ConfiguracionNoEncontrada(clave)

    valor = _convertir_valor_configuracion(datos.valor, actual.tipo)
    try:
        actualizado = parametros.set_param(
            db,
            clave,
            valor,
            actual.tipo,
            updated_by=actor.username,
        )
    except ValueError as exc:
        db.rollback()
        raise DatosInvalidos(str(exc)) from exc

    return ConfiguracionItem.model_validate(actualizado)


def crear_dueno_inicial(
    db: Session, username: str, password: str
) -> tuple[Usuario, bool]:
    """Crea el Dueño inicial. Si ya existe con ese rol, no lo modifica."""
    normalizado = _normalizar_username(username)
    existente = repository.obtener_por_username(db, normalizado)
    if existente is not None:
        if existente.rol == Rol.DUENIO:
            return existente, False
        raise UsuarioExistenteNoDuenio(normalizado)

    _validar_password(password)
    usuario = repository.crear_usuario(
        db,
        username=normalizado,
        password_hash=security.hash_password(password),
        rol=Rol.DUENIO,
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise UsernameDuplicado(normalizado) from exc

    db.refresh(usuario)
    return usuario, True
