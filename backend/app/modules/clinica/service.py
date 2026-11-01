"""Reglas de negocio para la historia clínica."""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.core import parametros
from app.modules.clinica import repository
from app.modules.clinica.models import Atencion, OrigenAtencion, TipoAtencion, VacunaAplicada
from app.modules.clinica.schemas import (
    AtencionCrear,
    AtencionDetalle,
    AtencionResumen,
    LibretaVacunasItem,
    VacunaAplicadaOut,
)
from app.modules.clinica.vacunas import estado_vacuna
from app.modules.padron import schemas as padron_schemas
from app.modules.padron import service as padron_service

CLAVE_DIAS_AVISO_VACUNA = "clinica.dias_aviso_vacuna"


class DatosInvalidos(Exception):
    """Datos que no cumplen las reglas de la historia clínica."""


class PacienteNoEncontrado(Exception):
    """El paciente no existe en el padrón."""


class EmpleadoNoEncontrado(Exception):
    """El empleado no existe en el padrón."""


class AtencionNoEncontrada(Exception):
    """La atención solicitada no existe."""


class RangoFechasInvalido(Exception):
    """El rango de fechas no es válido."""


def _validar_paciente(db: Session, paciente_id: int) -> None:
    if padron_service.obtener_paciente(db, paciente_id) is None:
        raise PacienteNoEncontrado()


def _empleado_o_error(
    db: Session, empleado_id: int
) -> padron_schemas.EmpleadoDetalle:
    empleado = padron_service.obtener_empleado(db, empleado_id)
    if empleado is None:
        raise EmpleadoNoEncontrado(f"No existe el empleado {empleado_id}")
    return empleado


def _nombre_empleado(db: Session, empleado_id: int | None) -> str | None:
    if empleado_id is None:
        return None
    empleado = padron_service.obtener_empleado(db, empleado_id)
    if empleado is None:
        return None
    return f"{empleado.nombre} {empleado.apellido}"


def _resumen(db: Session, atencion: Atencion) -> AtencionResumen:
    return AtencionResumen(
        id=atencion.id,
        paciente_id=atencion.paciente_id,
        tipo=atencion.tipo,
        fecha_hora=atencion.fecha_hora,
        veterinario_empleado_id=atencion.veterinario_empleado_id,
        veterinario_nombre=_nombre_empleado(db, atencion.veterinario_empleado_id),
        motivo=atencion.motivo,
        diagnostico=atencion.diagnostico,
        tratamiento=atencion.tratamiento,
        observaciones=atencion.observaciones,
        cirujano_externo_id=atencion.cirujano_externo_id,
        cirujano_externo_nombre=_nombre_empleado(db, atencion.cirujano_externo_id),
        cargo_id=atencion.cargo_id,
        origen=atencion.origen,
        texto_original=atencion.texto_original,
        rectifica_a_id=atencion.rectifica_a_id,
        rectificada=atencion.rectificada,
    )


def _detalle(db: Session, atencion: Atencion) -> AtencionDetalle:
    vacuna = repository.obtener_vacuna(db, atencion.id)
    return AtencionDetalle(
        **_resumen(db, atencion).model_dump(),
        created_by=atencion.created_by,
        created_at=atencion.created_at,
        vacuna=VacunaAplicadaOut.model_validate(vacuna) if vacuna else None,
    )


def _validar_empleados(
    db: Session,
    datos: AtencionCrear,
    empleado_por_defecto: int | None,
) -> tuple[int, int | None]:
    veterinario_id = datos.veterinario_empleado_id or empleado_por_defecto
    if veterinario_id is None:
        raise DatosInvalidos(
            "Debe indicar el veterinario que realizó la atención"
        )
    veterinario = _empleado_o_error(db, veterinario_id)
    if not veterinario.es_veterinario:
        raise DatosInvalidos("El empleado indicado no es veterinario")

    cirujano_id = datos.cirujano_externo_id
    if datos.tipo == TipoAtencion.CIRUGIA:
        if cirujano_id is None:
            raise DatosInvalidos("La cirugía requiere un cirujano externo")
        cirujano = _empleado_o_error(db, cirujano_id)
        if cirujano.tipo.value != "EXTERNO" or not cirujano.es_veterinario:
            raise DatosInvalidos(
                "El cirujano debe ser un veterinario externo"
            )
    elif cirujano_id is not None:
        raise DatosInvalidos("Solo una cirugía puede indicar cirujano externo")
    return veterinario_id, cirujano_id


def _crear_atencion(
    db: Session,
    paciente_id: int,
    datos: AtencionCrear,
    *,
    created_by: int,
    empleado_por_defecto: int | None,
    origen: OrigenAtencion,
    texto_original: str | None,
    rectifica_a_id: int | None = None,
) -> Atencion:
    _validar_paciente(db, paciente_id)
    veterinario_id, cirujano_id = _validar_empleados(
        db, datos, empleado_por_defecto
    )
    if datos.tipo == TipoAtencion.VACUNA and datos.vacuna is None:
        raise DatosInvalidos("La atención de tipo VACUNA requiere los datos de vacuna")
    if datos.tipo != TipoAtencion.VACUNA and datos.vacuna is not None:
        raise DatosInvalidos("Solo una atención de tipo VACUNA puede incluir vacuna")

    atencion = Atencion(
        paciente_id=paciente_id,
        tipo=datos.tipo,
        fecha_hora=datos.fecha_hora or datetime.now(UTC),
        veterinario_empleado_id=veterinario_id,
        motivo=datos.motivo,
        diagnostico=datos.diagnostico,
        tratamiento=datos.tratamiento,
        observaciones=datos.observaciones,
        cirujano_externo_id=cirujano_id,
        cargo_id=datos.cargo_id,
        origen=origen,
        texto_original=texto_original,
        rectifica_a_id=rectifica_a_id,
        created_by=created_by,
    )
    repository.crear_atencion(db, atencion)
    if datos.vacuna is not None:
        db.add(
            VacunaAplicada(
                atencion_id=atencion.id,
                nombre_vacuna=datos.vacuna.nombre_vacuna.strip(),
                lote=datos.vacuna.lote,
                fecha_aplicacion=datos.vacuna.fecha_aplicacion,
                proxima_dosis=datos.vacuna.proxima_dosis,
            )
        )
    return atencion


def registrar_atencion(
    db: Session,
    paciente_id: int,
    datos: AtencionCrear,
    *,
    created_by: int,
    empleado_por_defecto: int | None = None,
    origen: OrigenAtencion = OrigenAtencion.NORMAL,
    texto_original: str | None = None,
) -> AtencionDetalle:
    """Registra una atención clínica inmutable (RN-30 y RN-33)."""
    atencion = _crear_atencion(
        db,
        paciente_id,
        datos,
        created_by=created_by,
        empleado_por_defecto=empleado_por_defecto,
        origen=origen,
        texto_original=texto_original,
    )
    db.commit()
    db.refresh(atencion)
    return _detalle(db, atencion)


def atenciones_de_paciente(
    db: Session,
    paciente_id: int,
    *,
    tipo: TipoAtencion | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[AtencionResumen]:
    """Devuelve la línea de tiempo más reciente primero."""
    _validar_paciente(db, paciente_id)
    if desde is not None and hasta is not None and desde > hasta:
        raise RangoFechasInvalido()
    if limit < 1 or offset < 0:
        raise DatosInvalidos("La paginación no es válida")
    atenciones = repository.listar_atenciones(
        db,
        paciente_id,
        tipo=tipo,
        desde=desde,
        hasta=hasta,
        limit=limit,
        offset=offset,
    )
    return [_resumen(db, atencion) for atencion in atenciones]


def ultima_atencion(
    db: Session, paciente_id: int
) -> AtencionResumen | None:
    """Devuelve la atención vigente más reciente, excluyendo rectificadas."""
    _validar_paciente(db, paciente_id)
    atencion = repository.ultima_atencion(db, paciente_id)
    return _resumen(db, atencion) if atencion is not None else None


def obtener_atencion(db: Session, atencion_id: int) -> AtencionDetalle:
    atencion = repository.obtener_atencion(db, atencion_id)
    if atencion is None:
        raise AtencionNoEncontrada()
    return _detalle(db, atencion)


def rectificar_atencion(
    db: Session,
    atencion_id: int,
    datos: AtencionCrear,
    *,
    created_by: int,
    empleado_por_defecto: int | None = None,
) -> AtencionDetalle:
    """Crea una ficha correctiva y marca la original sin alterar sus datos."""
    original = repository.obtener_atencion(db, atencion_id)
    if original is None:
        raise AtencionNoEncontrada()
    nueva = _crear_atencion(
        db,
        original.paciente_id,
        datos,
        created_by=created_by,
        empleado_por_defecto=empleado_por_defecto,
        origen=OrigenAtencion.NORMAL,
        texto_original=None,
        rectifica_a_id=original.id,
    )
    if not original.rectificada:
        original.rectificada = True
    db.commit()
    db.refresh(nueva)
    return _detalle(db, nueva)


def libreta_vacunas(
    db: Session,
    paciente_id: int,
    *,
    hoy: date | None = None,
) -> list[LibretaVacunasItem]:
    """Lista vacunas y calcula el estado con la fecha y el parámetro vigentes."""
    _validar_paciente(db, paciente_id)
    dias_aviso = parametros.get_param(db, CLAVE_DIAS_AVISO_VACUNA)
    if not isinstance(dias_aviso, int) or isinstance(dias_aviso, bool):
        raise ValueError(f"{CLAVE_DIAS_AVISO_VACUNA} debe ser un entero")
    referencia = hoy or date.today()
    vacunas = repository.listar_vacunas(db, paciente_id)
    return [
        LibretaVacunasItem(
            atencion_id=vacuna.atencion_id,
            nombre_vacuna=vacuna.nombre_vacuna,
            lote=vacuna.lote,
            fecha_aplicacion=vacuna.fecha_aplicacion,
            proxima_dosis=vacuna.proxima_dosis,
            estado=estado_vacuna(
                vacuna.proxima_dosis,
                hoy=referencia,
                dias_aviso=dias_aviso,
            ),
        )
        for vacuna in vacunas
    ]
