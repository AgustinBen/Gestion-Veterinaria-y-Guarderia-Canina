"""Reglas de negocio del módulo identidad."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import parametros
from app.core.config import get_settings
from app.modules.identidad import permisos, repository, security
from app.modules.identidad.models import USERNAME_MAX_LENGTH, Usuario
from app.modules.identidad.permisos import Nivel, Recurso, Rol
from app.modules.identidad.schemas import (
    ConfiguracionItem,
    ConfiguracionUpdate,
    CuentaCrear,
    EmpleadoCuenta,
    LoginResponse,
    UsuarioActual,
    UsuarioActualizar,
    UsuarioCrear,
    UsuarioPublico,
)
from app.modules.padron import schemas as padron_schemas
from app.modules.padron import service as padron_service


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


class EmpleadoDuplicado(Exception):
    """El Padrón bloquea (DNI) o pide confirmar (teléfono/nombre) el empleado."""

    def __init__(self, detalle: dict[str, Any]) -> None:
        super().__init__("El empleado ya existe o hay posibles duplicados")
        self.detalle = detalle


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


def tiene_acceso(
    usuario: UsuarioActual, recurso: Recurso, nivel: Nivel = Nivel.LECTURA
) -> bool:
    """Indica si el usuario alcanza el nivel requerido para el recurso.

    Contrato público para consumo por otros módulos.
    """
    return permisos.puede(usuario.rol, recurso, nivel)


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


def _validar_empleado(db: Session, empleado_id: int | None) -> None:
    if (
        empleado_id is not None
        and padron_service.obtener_empleado(db, empleado_id) is None
    ):
        raise DatosInvalidos("El empleado indicado no existe")


ROLES_CON_EMPLEADO = (Rol.PERSONAL, Rol.VETERINARIO)


def _crear_empleado_de_cuenta(
    db: Session, rol: Rol, datos: EmpleadoCuenta
) -> int:
    """Da de alta el empleado interno de una cuenta vía el servicio del Padrón."""
    try:
        empleado = padron_service.crear_empleado(
            db,
            padron_schemas.EmpleadoNuevo(
                persona=padron_schemas.PersonaNueva(
                    nombre=datos.nombre,
                    apellido=datos.apellido,
                    dni=datos.dni,
                    telefonos=[datos.telefono],
                    confirmar_duplicado=datos.confirmar_duplicado,
                    persona_coincidente_id=datos.persona_coincidente_id,
                ),
                es_veterinario=rol == Rol.VETERINARIO,
                especialidad=(
                    (datos.especialidad or "").strip() or None
                    if rol == Rol.VETERINARIO
                    else None
                ),
            ),
        )
    except padron_service.DniDuplicado as exc:
        raise EmpleadoDuplicado(
            {"codigo": "DNI_DUPLICADO", "persona": exc.persona.model_dump()}
        ) from exc
    except padron_service.PosibleDuplicado as exc:
        raise EmpleadoDuplicado(
            {
                "codigo": "POSIBLE_DUPLICADO",
                "coincidencias": [c.model_dump() for c in exc.coincidencias],
            }
        ) from exc
    except padron_service.DatosInvalidos as exc:
        raise DatosInvalidos(str(exc)) from exc
    return empleado.persona_id


def crear_usuario(db: Session, datos: UsuarioCrear) -> UsuarioPublico:
    """Crea un usuario con username normalizado y contraseña hasheada."""
    username = _normalizar_username(datos.username)
    _validar_password(datos.password)
    _validar_empleado(db, datos.empleado_id)

    if repository.obtener_por_username(db, username) is not None:
        raise UsernameDuplicado(username)

    return _guardar_usuario(
        db, username, datos.password, datos.rol, datos.empleado_id
    )


def crear_cuenta(db: Session, datos: CuentaCrear) -> UsuarioPublico:
    """Crea una cuenta; PERSONAL y VETERINARIO crean además su empleado interno.

    El empleado se da de alta en el Padrón (``padron.service.crear_empleado``)
    y queda vinculado por ``empleado_id``. Se valida todo lo propio antes de
    escribir el empleado para no dejar fichas huérfanas.
    """
    username = _normalizar_username(datos.username)
    _validar_password(datos.password)

    if datos.rol in ROLES_CON_EMPLEADO:
        if datos.empleado is None:
            raise DatosInvalidos(
                "Las cuentas de personal y veterinario requieren los datos "
                "del empleado"
            )
    elif datos.empleado is not None:
        raise DatosInvalidos("Este rol no lleva datos de empleado")

    if repository.obtener_por_username(db, username) is not None:
        raise UsernameDuplicado(username)

    empleado_id: int | None = None
    if datos.empleado is not None:
        empleado_id = _crear_empleado_de_cuenta(db, datos.rol, datos.empleado)

    return _guardar_usuario(db, username, datos.password, datos.rol, empleado_id)


def _guardar_usuario(
    db: Session,
    username: str,
    password: str,
    rol: Rol,
    empleado_id: int | None,
) -> UsuarioPublico:
    usuario = repository.crear_usuario(
        db,
        username=username,
        password_hash=security.hash_password(password),
        rol=rol,
        empleado_id=empleado_id,
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

    nuevo_empleado_id = usuario.empleado_id
    if "empleado_id" in campos:
        nuevo_empleado_id = datos.empleado_id
        _validar_empleado(db, nuevo_empleado_id)

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
    if "empleado_id" in campos:
        usuario.empleado_id = nuevo_empleado_id
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
