"""Reglas de negocio para la historia clínica."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.orm import Session

from app.core import parametros
from app.core.db import transaccion_inmediata
from app.modules.clinica import almacenamiento, estados, repository
from app.modules.clinica.horarios import validar_horarios
from app.modules.clinica.models import (
    Adjunto,
    Atencion,
    EstadoTurno,
    Estudio,
    FranjaTurnoPersonal,
    HorarioAtencion,
    MedioEventoExterno,
    OrigenAtencion,
    TipoAtencion,
    TipoEventoExterno,
    TipoTurnoMedico,
    Turno,
    TurnoExternoEvento,
    TurnoPersonal,
    VacunaAplicada,
)
from app.modules.clinica.schemas import (
    AdjuntoResumen,
    AgendaDiaOut,
    AtencionCrear,
    AtencionDetalle,
    AtencionResumen,
    EmpleadoTraspaso,
    EstudioCrear,
    EstudioResumen,
    EventoExternoOut,
    ExternoConfirmarIn,
    ExternoContactadoIn,
    ExternoReemplazarIn,
    HorarioAtencionIn,
    HorarioAtencionOut,
    LibretaVacunasItem,
    TurnoAtendidoOut,
    TurnoCrear,
    TurnoOut,
    TurnoPersonalDefIn,
    TurnoPersonalDefOut,
    TurnoPersonalIn,
    TurnoPersonalOut,
    TurnoReprogramar,
    TurnosPersonalDefinicionOut,
    VacunaAplicadaOut,
    VentanaTraspasoOut,
)
from app.modules.clinica.traspaso import TurnoDefinidoConPersonal, ventanas_traspaso
from app.modules.clinica.vacunas import estado_vacuna
from app.modules.cobros import service as cobros_service
from app.modules.padron import schemas as padron_schemas
from app.modules.padron import service as padron_service

CLAVE_DIAS_AVISO_VACUNA = "clinica.dias_aviso_vacuna"
CLAVE_MINUTOS_TRASPASO = "clinica.minutos_traspaso"
CLAVE_TRASPASO_BLOQUEA_TURNOS = "clinica.traspaso_bloquea_turnos"
CLAVE_DURACION_TURNO_SUGERIDA = "clinica.duracion_turno_sugerida_min"


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


class EstudioNoEncontrado(Exception):
    """El estudio solicitado no existe."""


class AdjuntoNoEncontrado(Exception):
    """El adjunto solicitado no existe."""


class AgendaError(Exception):
    codigo = "AGENDA_INVALIDA"
    status_code = 422


class HorarioNoDefinido(AgendaError):
    codigo = "HORARIO_NO_DEFINIDO"
    status_code = 409


class TurnoFueraDeHorario(AgendaError):
    codigo = "FUERA_DE_HORARIO"


class TurnoSolapado(AgendaError):
    codigo = "SOLAPADO"
    status_code = 409


class TraspasoBloqueado(AgendaError):
    codigo = "TRASPASO_BLOQUEADO"
    status_code = 409


class TurnoNoEncontrado(AgendaError):
    codigo = "TURNO_NO_ENCONTRADO"
    status_code = 404


class EstadoTurnoInvalido(AgendaError):
    codigo = "TRANSICION_INVALIDA"
    status_code = 409


class EmpleadoTurnoInvalido(AgendaError):
    codigo = "EMPLEADO_INVALIDO"


class EmpleadoNoDisponible(AgendaError):
    codigo = "EMPLEADO_NO_DISPONIBLE"


class PacienteTurnoNoEncontrado(AgendaError):
    codigo = "PACIENTE_NO_ENCONTRADO"


class TurnoPersonalDuplicado(AgendaError):
    codigo = "TURNO_PERSONAL_DUPLICADO"
    status_code = 409


class TurnoPersonalNoEncontrado(AgendaError):
    codigo = "TURNO_PERSONAL_NO_ENCONTRADO"
    status_code = 404


class RangoAgendaInvalido(AgendaError):
    codigo = "RANGO_INVALIDO"


class AtencionTurnoNoEncontrada(AgendaError):
    codigo = "ATENCION_NO_ENCONTRADA"


class ExternoTurnoInvalido(AgendaError):
    codigo = "EXTERNO_INVALIDO"


class ExternoOcupado(AgendaError):
    codigo = "EXTERNO_OCUPADO"
    status_code = 409


class TurnoNoEsCirugia(AgendaError):
    codigo = "TURNO_NO_ES_CIRUGIA"


class AtencionCirugiaInvalida(AgendaError):
    codigo = "ATENCION_CIRUGIA_INVALIDA"


class CirugiaSinConfirmacion(AgendaError):
    codigo = "CIRUGIA_SIN_CONFIRMACION"
    status_code = 409


@dataclass(frozen=True)
class AdjuntoDescarga:
    nombre_archivo: str
    nombre_original: str
    tipo_mime: str


def _validar_paciente(db: Session, paciente_id: int) -> None:
    if padron_service.obtener_paciente(db, paciente_id) is None:
        raise PacienteNoEncontrado()


def _empleado_o_error(db: Session, empleado_id: int) -> padron_schemas.EmpleadoDetalle:
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
        raise DatosInvalidos("Debe indicar el veterinario que realizó la atención")
    veterinario = _empleado_o_error(db, veterinario_id)
    if not veterinario.es_veterinario:
        raise DatosInvalidos("El empleado indicado no es veterinario")

    cirujano_id = datos.cirujano_externo_id
    if datos.tipo == TipoAtencion.CIRUGIA:
        if cirujano_id is None:
            raise DatosInvalidos("La cirugía requiere un cirujano externo")
        cirujano = _empleado_o_error(db, cirujano_id)
        if cirujano.tipo.value != "EXTERNO" or not cirujano.es_veterinario:
            raise DatosInvalidos("El cirujano debe ser un veterinario externo")
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
    veterinario_id, cirujano_id = _validar_empleados(db, datos, empleado_por_defecto)
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


def ultima_atencion(db: Session, paciente_id: int) -> AtencionResumen | None:
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


def _adjunto_resumen(adjunto: Adjunto) -> AdjuntoResumen:
    return AdjuntoResumen(
        id=adjunto.id,
        nombre_original=adjunto.nombre_original,
        tipo_mime=adjunto.tipo_mime,
        tamano_bytes=adjunto.tamano_bytes,
        sha256=adjunto.sha256,
        created_by=adjunto.created_by,
        created_at=adjunto.created_at,
    )


def _estudio_resumen(estudio: Estudio, adjuntos: list[Adjunto] | None = None) -> EstudioResumen:
    return EstudioResumen(
        id=estudio.id,
        paciente_id=estudio.paciente_id,
        atencion_id=estudio.atencion_id,
        tipo=estudio.tipo,
        fecha=estudio.fecha,
        descripcion=estudio.descripcion,
        realizado_por_empleado_id=estudio.realizado_por_empleado_id,
        cargo_id=estudio.cargo_id,
        created_by=estudio.created_by,
        created_at=estudio.created_at,
        adjuntos=[_adjunto_resumen(adjunto) for adjunto in adjuntos or []],
    )


def registrar_estudio(
    db: Session,
    paciente_id: int,
    datos: EstudioCrear,
    *,
    created_by: int,
) -> EstudioResumen:
    _validar_paciente(db, paciente_id)
    empleado = _empleado_o_error(db, datos.realizado_por_empleado_id)
    if not empleado.es_veterinario:
        raise DatosInvalidos("El realizador debe ser un veterinario")

    descripcion = datos.descripcion.strip()
    if not descripcion:
        raise DatosInvalidos("La descripción no puede estar vacía")

    costo_centavos = datos.costo_centavos
    titular_principal = None
    if costo_centavos is not None:
        titulares = padron_service.titulares_vigentes(db, paciente_id)
        titular_principal = next((titular for titular in titulares if titular.principal), None)
        if titular_principal is None:
            raise DatosInvalidos("El paciente no tiene titular principal vigente")

    estudio = Estudio(
        paciente_id=paciente_id,
        tipo=datos.tipo,
        fecha=datos.fecha,
        descripcion=descripcion,
        realizado_por_empleado_id=datos.realizado_por_empleado_id,
        created_by=created_by,
    )
    try:
        repository.crear_estudio(db, estudio)
        if costo_centavos is not None and titular_principal is not None:
            cargo = cobros_service.crear_cargo(
                db,
                persona_id=titular_principal.persona_id,
                concepto=f"Estudio {datos.tipo.value}",
                total_centavos=costo_centavos,
                paciente_id=paciente_id,
                referencia_tipo="ESTUDIO",
                referencia_id=estudio.id,
                usuario_id=created_by,
                transaccion_externa=True,
            )
            estudio.cargo_id = cargo.id
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(estudio)
    return _estudio_resumen(estudio)


def listar_estudios(db: Session, paciente_id: int) -> list[EstudioResumen]:
    _validar_paciente(db, paciente_id)
    estudios = repository.listar_estudios(db, paciente_id)
    adjuntos_por_estudio: dict[int, list[Adjunto]] = defaultdict(list)
    for adjunto in repository.listar_adjuntos(db, [estudio.id for estudio in estudios]):
        adjuntos_por_estudio[adjunto.estudio_id].append(adjunto)
    return [_estudio_resumen(estudio, adjuntos_por_estudio[estudio.id]) for estudio in estudios]


def verificar_estudio(db: Session, estudio_id: int) -> None:
    if repository.obtener_estudio(db, estudio_id) is None:
        raise EstudioNoEncontrado()


def registrar_adjunto(
    db: Session,
    estudio_id: int,
    archivo: almacenamiento.ArchivoAlmacenado,
    *,
    nombre_original: str,
    created_by: int,
) -> AdjuntoResumen:
    verificar_estudio(db, estudio_id)
    adjunto = Adjunto(
        estudio_id=estudio_id,
        nombre_original=nombre_original,
        nombre_archivo=archivo.nombre_archivo,
        tipo_mime=archivo.tipo_mime,
        tamano_bytes=archivo.tamano_bytes,
        sha256=archivo.sha256,
        created_by=created_by,
    )
    try:
        repository.crear_adjunto(db, adjunto)
        db.commit()
    except Exception:
        db.rollback()
        almacenamiento.eliminar(archivo.ruta)
        raise
    db.refresh(adjunto)
    return _adjunto_resumen(adjunto)


def obtener_adjunto_para_descarga(db: Session, adjunto_id: int) -> AdjuntoDescarga:
    adjunto = repository.obtener_adjunto(db, adjunto_id)
    if adjunto is None:
        raise AdjuntoNoEncontrado()
    return AdjuntoDescarga(
        nombre_archivo=adjunto.nombre_archivo,
        nombre_original=adjunto.nombre_original,
        tipo_mime=adjunto.tipo_mime,
    )


def _horario_out(horario: HorarioAtencion) -> HorarioAtencionOut:
    return HorarioAtencionOut(
        id=horario.id,
        dia_semana=horario.dia_semana,
        hora_desde=horario.hora_desde,
        hora_hasta=horario.hora_hasta,
    )


def horarios_atencion(db: Session) -> list[HorarioAtencionOut]:
    return [_horario_out(item) for item in repository.listar_horarios(db)]


def reemplazar_horarios_atencion(
    db: Session, horarios: list[HorarioAtencionIn]
) -> list[HorarioAtencionOut]:
    validar_horarios(horarios)
    with transaccion_inmediata(db):
        resultado = repository.reemplazar_horarios(db, horarios)
    return [_horario_out(item) for item in resultado]


def definicion_turnos_personal(db: Session) -> TurnosPersonalDefinicionOut:
    definiciones = repository.listar_definiciones_turno_personal(db)
    return TurnosPersonalDefinicionOut(
        turnos=[
            TurnoPersonalDefOut(
                id=item.id,
                turno=item.turno,
                hora_desde=item.hora_desde,
                hora_hasta=item.hora_hasta,
            )
            for item in definiciones
        ]
    )


def reemplazar_definicion_turnos_personal(
    db: Session, definiciones: list[TurnoPersonalDefIn]
) -> TurnosPersonalDefinicionOut:
    with transaccion_inmediata(db):
        resultado = repository.reemplazar_definiciones_turno_personal(db, definiciones)
    return TurnosPersonalDefinicionOut(
        turnos=[
            TurnoPersonalDefOut(
                id=item.id,
                turno=item.turno,
                hora_desde=item.hora_desde,
                hora_hasta=item.hora_hasta,
            )
            for item in resultado
        ]
    )


def _nombre_empleado_turno(db: Session, empleado_id: int) -> str:
    empleado = _empleado_o_error(db, empleado_id)
    return f"{empleado.nombre} {empleado.apellido}"


def _turno_personal_out(db: Session, item: TurnoPersonal) -> TurnoPersonalOut:
    return TurnoPersonalOut(
        empleado_id=item.empleado_id,
        fecha=item.fecha,
        turno=item.turno,
        empleado_nombre=_nombre_empleado_turno(db, item.empleado_id),
    )


def turnos_personal(
    db: Session,
    *,
    desde: date | None = None,
    hasta: date | None = None,
    empleado_id: int | None = None,
) -> list[TurnoPersonalOut]:
    if desde is not None and hasta is not None and desde > hasta:
        raise RangoAgendaInvalido("La fecha desde debe ser anterior o igual a hasta")
    return [
        _turno_personal_out(db, item)
        for item in repository.listar_turnos_personal(
            db, desde=desde, hasta=hasta, empleado_id=empleado_id
        )
    ]


def asignar_turno_personal(db: Session, datos: TurnoPersonalIn) -> TurnoPersonalOut:
    empleado = padron_service.obtener_empleado(db, datos.empleado_id)
    if (
        empleado is None
        or empleado.tipo.value != "INTERNO"
        or not empleado.activo
    ):
        raise EmpleadoNoDisponible("El turno requiere un empleado interno y activo")

    with transaccion_inmediata(db):
        if repository.obtener_turno_personal(
            db, datos.empleado_id, datos.fecha, datos.turno
        ):
            raise TurnoPersonalDuplicado("El empleado ya tiene asignado ese turno")
        asignado = repository.crear_turno_personal(
            db,
            TurnoPersonal(
                empleado_id=datos.empleado_id,
                fecha=datos.fecha,
                turno=datos.turno,
            ),
        )
    return _turno_personal_out(db, asignado)


def quitar_turno_personal(
    db: Session, datos: TurnoPersonalIn
) -> None:
    with transaccion_inmediata(db):
        asignado = repository.obtener_turno_personal(
            db, datos.empleado_id, datos.fecha, datos.turno
        )
        if asignado is None:
            raise TurnoPersonalNoEncontrado("No existe esa asignación de turno")
        repository.eliminar_turno_personal(db, asignado)


def _turno_out(turno: Turno) -> TurnoOut:
    return TurnoOut(
        id=turno.id,
        paciente_id=turno.paciente_id,
        tipo=turno.tipo,
        veterinario_empleado_id=turno.veterinario_empleado_id,
        inicio=turno.inicio,
        fin=turno.fin,
        estado=turno.estado,
        motivo=turno.motivo,
        atencion_id=turno.atencion_id,
        externo_actual_id=turno.externo_actual_id,
        created_by=turno.created_by,
        created_at=turno.created_at,
    )


def _validar_medico(
    db: Session,
    paciente_id: int,
    veterinario_id: int,
) -> None:
    if padron_service.obtener_paciente(db, paciente_id) is None:
        raise PacienteTurnoNoEncontrado("El paciente no existe")
    empleado = padron_service.obtener_empleado(db, veterinario_id)
    if (
        empleado is None
        or empleado.tipo.value != "INTERNO"
        or not empleado.es_veterinario
    ):
        raise EmpleadoTurnoInvalido(
            "El veterinario debe ser un empleado interno con perfil veterinario"
        )


def _validar_externo(
    db: Session, externo_id: int
) -> padron_schemas.EmpleadoDetalle:
    empleado = padron_service.obtener_empleado(db, externo_id)
    if (
        empleado is None
        or empleado.tipo.value != "EXTERNO"
        or not empleado.es_veterinario
    ):
        raise ExternoTurnoInvalido(
            "El externo debe ser un veterinario externo registrado"
        )
    return empleado


def _fecha_local_valida(inicio: datetime, fin: datetime) -> None:
    if inicio.tzinfo is not None or fin.tzinfo is not None:
        raise AgendaError("Los turnos deben usar la hora local sin zona horaria")
    if inicio >= fin:
        raise AgendaError("El fin debe ser posterior al inicio")
    if inicio.date() != fin.date():
        raise TurnoFueraDeHorario("El turno debe quedar dentro del mismo día de atención")


def _datos_turnos_asignados(
    db: Session,
    dia: date,
) -> list[TurnoDefinidoConPersonal]:
    fecha_anterior = dia - timedelta(days=1)
    definiciones = {
        item.turno: item for item in repository.listar_definiciones_turno_personal(db)
    }
    asignaciones = repository.listar_turnos_personal(
        db, desde=fecha_anterior, hasta=dia
    )
    empleados_por_fecha_turno: dict[
        tuple[date, FranjaTurnoPersonal], list[EmpleadoTraspaso]
    ] = {}
    for asignacion in asignaciones:
        empleados_por_fecha_turno.setdefault(
            (asignacion.fecha, asignacion.turno), []
        ).append(
            EmpleadoTraspaso(
                empleado_id=asignacion.empleado_id,
                nombre=_nombre_empleado_turno(db, asignacion.empleado_id),
            )
        )

    resultado: list[TurnoDefinidoConPersonal] = []
    for fecha in (fecha_anterior, dia):
        for nombre_turno, definicion in definiciones.items():
            resultado.append(
                TurnoDefinidoConPersonal(
                    fecha=fecha,
                    turno=nombre_turno,
                    hora_desde=definicion.hora_desde,
                    hora_hasta=definicion.hora_hasta,
                    empleados=tuple(
                        empleados_por_fecha_turno.get((fecha, nombre_turno), [])
                    ),
                )
            )
    return resultado


def ventanas_traspaso_del_dia(db: Session, dia: date) -> list[VentanaTraspasoOut]:
    minutos = parametros.get_param(db, CLAVE_MINUTOS_TRASPASO)
    if not isinstance(minutos, int) or isinstance(minutos, bool):
        raise ValueError(f"{CLAVE_MINUTOS_TRASPASO} debe ser un entero")
    return ventanas_traspaso(dia, _datos_turnos_asignados(db, dia), minutos)


def _validar_turno(
    db: Session,
    *,
    paciente_id: int,
    veterinario_id: int,
    inicio: datetime,
    fin: datetime,
    ahora: datetime,
    excluir_id: int | None = None,
) -> None:
    _fecha_local_valida(inicio, fin)
    if inicio < ahora:
        raise AgendaError("No se pueden agendar turnos en el pasado")
    _validar_medico(db, paciente_id, veterinario_id)

    horarios = repository.listar_horarios(db)
    if not horarios:
        raise HorarioNoDefinido("Aún no se definieron horarios de atención")
    franjas_del_dia = [
        item
        for item in horarios
        if item.dia_semana == inicio.weekday()
        and item.hora_desde <= inicio.time()
        and fin.time() <= item.hora_hasta
    ]
    if not franjas_del_dia:
        raise TurnoFueraDeHorario("El turno debe quedar dentro del horario de atención")

    if repository.turno_solapado(
        db,
        paciente_id=paciente_id,
        veterinario_id=veterinario_id,
        inicio=inicio,
        fin=fin,
        excluir_id=excluir_id,
    ):
        raise TurnoSolapado("El veterinario o el paciente ya tiene un turno en ese horario")

    bloquea_traspaso = parametros.get_param(db, CLAVE_TRASPASO_BLOQUEA_TURNOS)
    if not isinstance(bloquea_traspaso, bool):
        raise ValueError(f"{CLAVE_TRASPASO_BLOQUEA_TURNOS} debe ser booleano")
    if bloquea_traspaso:
        ventanas = ventanas_traspaso_del_dia(db, inicio.date())
        if any(ventana.inicio < fin and ventana.fin > inicio for ventana in ventanas):
            raise TraspasoBloqueado("El turno se superpone con una ventana de traspaso")


def agendar_turno(
    db: Session,
    datos: TurnoCrear,
    *,
    created_by: int,
    ahora: datetime | None = None,
) -> TurnoOut:
    referencia = ahora or datetime.now()
    es_cirugia = datos.tipo == TipoTurnoMedico.CIRUGIA
    if es_cirugia and datos.externo_empleado_id is None:
        raise ExternoTurnoInvalido("La cirugía requiere un veterinario externo")
    if not es_cirugia and datos.externo_empleado_id is not None:
        raise ExternoTurnoInvalido(
            "Solo una cirugía puede indicar un veterinario externo"
        )
    with transaccion_inmediata(db):
        _validar_turno(
            db,
            paciente_id=datos.paciente_id,
            veterinario_id=datos.veterinario_empleado_id,
            inicio=datos.inicio,
            fin=datos.fin,
            ahora=referencia,
        )
        externo_id = datos.externo_empleado_id
        if externo_id is not None:
            _validar_externo(db, externo_id)
        turno = repository.crear_turno(
            db,
            Turno(
                paciente_id=datos.paciente_id,
                tipo=datos.tipo,
                veterinario_empleado_id=datos.veterinario_empleado_id,
                inicio=datos.inicio,
                fin=datos.fin,
                estado=(
                    EstadoTurno.PENDIENTE_EXTERNO
                    if es_cirugia
                    else EstadoTurno.PROGRAMADO
                ),
                motivo=datos.motivo,
                externo_actual_id=externo_id,
                created_by=created_by,
            ),
        )
    db.refresh(turno)
    return _turno_out(turno)


def obtener_turno(db: Session, turno_id: int) -> TurnoOut:
    turno = repository.obtener_turno(db, turno_id)
    if turno is None:
        raise TurnoNoEncontrado("Turno no encontrado")
    return _turno_out(turno)


def _evento_out(
    db: Session, evento: TurnoExternoEvento, *, ver_costo: bool
) -> EventoExternoOut:
    return EventoExternoOut(
        id=evento.id,
        turno_id=evento.turno_id,
        tipo=evento.tipo,
        externo_empleado_id=evento.externo_empleado_id,
        externo_nombre=_nombre_empleado(db, evento.externo_empleado_id),
        medio=evento.medio,
        nota=evento.nota,
        costo_acordado_centavos=(
            evento.costo_acordado_centavos if ver_costo else None
        ),
        costo_registrado=evento.costo_acordado_centavos is not None,
        usuario_id=evento.usuario_id,
        created_at=evento.created_at,
    )


def _turno_cirugia_pendiente(db: Session, turno_id: int) -> tuple[Turno, int]:
    turno = repository.obtener_turno(db, turno_id)
    if turno is None:
        raise TurnoNoEncontrado("Turno no encontrado")
    if turno.tipo != TipoTurnoMedico.CIRUGIA:
        raise TurnoNoEsCirugia("El turno no es una cirugía")
    if turno.estado != EstadoTurno.PENDIENTE_EXTERNO:
        raise EstadoTurnoInvalido(
            "Solo se puede gestionar el externo de una cirugía pendiente"
        )
    if turno.externo_actual_id is None:
        raise ExternoTurnoInvalido("El turno no tiene un veterinario externo asignado")
    return turno, turno.externo_actual_id


def _crear_evento_externo(
    db: Session,
    turno: Turno,
    tipo: TipoEventoExterno,
    *,
    usuario_id: int,
    externo_id: int,
    medio: MedioEventoExterno | None = None,
    nota: str | None = None,
    costo_centavos: int | None = None,
) -> TurnoExternoEvento:
    evento = TurnoExternoEvento(
        turno_id=turno.id,
        tipo=tipo,
        externo_empleado_id=externo_id,
        medio=medio,
        nota=nota,
        costo_acordado_centavos=costo_centavos,
        usuario_id=usuario_id,
    )
    return repository.crear_evento_externo(db, evento)


def registrar_contacto_externo(
    db: Session,
    turno_id: int,
    datos: ExternoContactadoIn,
    *,
    usuario_id: int,
    ver_costo: bool,
) -> EventoExternoOut:
    with transaccion_inmediata(db):
        turno, externo_id = _turno_cirugia_pendiente(db, turno_id)
        nota = datos.nota.strip() if datos.nota is not None else None
        evento = _crear_evento_externo(
            db,
            turno,
            TipoEventoExterno.CONTACTADO,
            usuario_id=usuario_id,
            externo_id=externo_id,
            medio=datos.medio,
            nota=nota or None,
        )
    db.refresh(evento)
    return _evento_out(db, evento, ver_costo=ver_costo)


def confirmar_externo(
    db: Session,
    turno_id: int,
    datos: ExternoConfirmarIn,
    *,
    usuario_id: int,
    ver_costo: bool,
) -> EventoExternoOut:
    with transaccion_inmediata(db):
        turno, externo_id = _turno_cirugia_pendiente(db, turno_id)
        if repository.turno_externo_ocupado(
            db,
            externo_id=externo_id,
            inicio=turno.inicio,
            fin=turno.fin,
            excluir_id=turno.id,
        ):
            raise ExternoOcupado(
                "El veterinario externo ya tiene otra cirugía confirmada en ese horario"
            )
        turno.estado = EstadoTurno.CONFIRMADO
        evento = _crear_evento_externo(
            db,
            turno,
            TipoEventoExterno.CONFIRMADO,
            usuario_id=usuario_id,
            externo_id=externo_id,
            costo_centavos=datos.costo_acordado_centavos,
        )
    db.refresh(evento)
    return _evento_out(db, evento, ver_costo=ver_costo)


def rechazar_externo(
    db: Session,
    turno_id: int,
    motivo: str,
    *,
    usuario_id: int,
    ver_costo: bool,
) -> EventoExternoOut:
    texto = motivo.strip()
    if not texto:
        raise AgendaError("El motivo del rechazo es obligatorio")
    with transaccion_inmediata(db):
        turno, externo_id = _turno_cirugia_pendiente(db, turno_id)
        evento = _crear_evento_externo(
            db,
            turno,
            TipoEventoExterno.RECHAZADO,
            usuario_id=usuario_id,
            externo_id=externo_id,
            nota=texto,
        )
    db.refresh(evento)
    return _evento_out(db, evento, ver_costo=ver_costo)


def reemplazar_externo(
    db: Session,
    turno_id: int,
    datos: ExternoReemplazarIn,
    *,
    usuario_id: int,
    ver_costo: bool,
) -> EventoExternoOut:
    with transaccion_inmediata(db):
        turno, _externo_actual = _turno_cirugia_pendiente(db, turno_id)
        _validar_externo(db, datos.externo_empleado_id)
        evento = _crear_evento_externo(
            db,
            turno,
            TipoEventoExterno.REEMPLAZADO,
            usuario_id=usuario_id,
            externo_id=datos.externo_empleado_id,
        )
        turno.externo_actual_id = datos.externo_empleado_id
    db.refresh(evento)
    return _evento_out(db, evento, ver_costo=ver_costo)


def eventos_externo_turno(
    db: Session, turno_id: int, *, ver_costo: bool
) -> list[EventoExternoOut]:
    turno = repository.obtener_turno(db, turno_id)
    if turno is None:
        raise TurnoNoEncontrado("Turno no encontrado")
    if turno.tipo != TipoTurnoMedico.CIRUGIA:
        return []
    return [
        _evento_out(db, evento, ver_costo=ver_costo)
        for evento in repository.listar_eventos_externos(db, turno_id)
    ]


def listar_turnos(
    db: Session,
    *,
    desde: date | None = None,
    hasta: date | None = None,
    veterinario_id: int | None = None,
    paciente_id: int | None = None,
    estado: EstadoTurno | None = None,
) -> list[TurnoOut]:
    if desde is not None and hasta is not None and desde > hasta:
        raise RangoAgendaInvalido("La fecha desde debe ser anterior o igual a hasta")
    return [
        _turno_out(item)
        for item in repository.listar_turnos(
            db,
            desde=desde,
            hasta=hasta,
            veterinario_id=veterinario_id,
            paciente_id=paciente_id,
            estado=estado,
        )
    ]


def reprogramar_turno(
    db: Session,
    turno_id: int,
    datos: TurnoReprogramar,
    *,
    ahora: datetime | None = None,
) -> TurnoOut:
    with transaccion_inmediata(db):
        turno = repository.obtener_turno(db, turno_id)
        if turno is None:
            raise TurnoNoEncontrado("Turno no encontrado")
        if not estados.puede_reprogramar(turno.estado):
            raise EstadoTurnoInvalido("El estado actual no permite reprogramar")
        nuevo_inicio = datos.inicio if datos.inicio is not None else turno.inicio
        nuevo_fin = datos.fin if datos.fin is not None else turno.fin
        veterinario_id = (
            datos.veterinario_empleado_id
            if datos.veterinario_empleado_id is not None
            else turno.veterinario_empleado_id
        )
        _validar_turno(
            db,
            paciente_id=turno.paciente_id,
            veterinario_id=veterinario_id,
            inicio=nuevo_inicio,
            fin=nuevo_fin,
            ahora=ahora or datetime.now(),
            excluir_id=turno.id,
        )
        turno.inicio = nuevo_inicio
        turno.fin = nuevo_fin
        turno.veterinario_empleado_id = veterinario_id
    db.refresh(turno)
    return _turno_out(turno)


def _cambiar_estado(
    db: Session,
    turno_id: int,
    nuevo_estado: EstadoTurno,
    *,
    motivo: str | None = None,
    atencion_id: int | None = None,
) -> TurnoOut:
    with transaccion_inmediata(db):
        turno = repository.obtener_turno(db, turno_id)
        if turno is None:
            raise TurnoNoEncontrado("Turno no encontrado")
        if not estados.puede_transicionar(turno.estado, nuevo_estado):
            raise EstadoTurnoInvalido(
                f"No se puede cambiar de {turno.estado.value} a {nuevo_estado.value}"
            )
        if atencion_id is not None:
            atencion = repository.obtener_atencion(db, atencion_id)
            if atencion is None or atencion.paciente_id != turno.paciente_id:
                raise AtencionTurnoNoEncontrada(
                    "La atención no existe o no corresponde al paciente del turno"
                )
        turno.estado = nuevo_estado
        if motivo is not None:
            turno.motivo = motivo
        if nuevo_estado == EstadoTurno.ATENDIDO:
            turno.atencion_id = atencion_id
    db.refresh(turno)
    return _turno_out(turno)


def cancelar_turno(db: Session, turno_id: int, motivo: str) -> TurnoOut:
    texto = motivo.strip()
    if not texto:
        raise AgendaError("El motivo de cancelación es obligatorio")
    return _cambiar_estado(
        db, turno_id, EstadoTurno.CANCELADO, motivo=texto
    )


def marcar_turno_ausente(db: Session, turno_id: int) -> TurnoOut:
    return _cambiar_estado(db, turno_id, EstadoTurno.AUSENTE)


def _atencion_cirugia_para_turno(
    db: Session, turno: Turno, atencion_id: int | None
) -> Atencion:
    if atencion_id is None:
        raise AtencionCirugiaInvalida(
            "La cirugía requiere la atención de tipo CIRUGIA"
        )
    atencion = repository.obtener_atencion(db, atencion_id)
    if atencion is None or atencion.paciente_id != turno.paciente_id:
        raise AtencionTurnoNoEncontrada(
            "La atención no existe o no corresponde al paciente del turno"
        )
    if atencion.tipo != TipoAtencion.CIRUGIA:
        raise AtencionCirugiaInvalida("La atención debe ser de tipo CIRUGIA")
    if atencion.cirujano_externo_id != turno.externo_actual_id:
        raise AtencionCirugiaInvalida(
            "La atención debe tener el mismo veterinario externo del turno"
        )
    return atencion


def marcar_turno_atendido(
    db: Session,
    turno_id: int,
    atencion_id: int | None,
    *,
    usuario_id: int,
) -> TurnoAtendidoOut:
    gasto_registrado = False
    with transaccion_inmediata(db):
        turno = repository.obtener_turno(db, turno_id)
        if turno is None:
            raise TurnoNoEncontrado("Turno no encontrado")
        if not estados.puede_transicionar(turno.estado, EstadoTurno.ATENDIDO):
            raise EstadoTurnoInvalido(
                f"No se puede cambiar de {turno.estado.value} a ATENDIDO"
            )
        if turno.tipo == TipoTurnoMedico.CIRUGIA:
            atencion = _atencion_cirugia_para_turno(db, turno, atencion_id)
            externo_id = turno.externo_actual_id
            if externo_id is None:
                raise AtencionCirugiaInvalida(
                    "El turno no tiene un veterinario externo asignado"
                )
            evento = repository.ultimo_evento_confirmado(db, turno.id)
            if evento is None or evento.costo_acordado_centavos is None:
                raise CirugiaSinConfirmacion(
                    "La cirugía no tiene un externo confirmado con costo"
                )
            turno.estado = EstadoTurno.ATENDIDO
            turno.atencion_id = atencion.id
            db.flush()
            cobros_service.registrar_gasto_externo(
                db,
                empleado_externo_id=externo_id,
                descripcion="Cirugía",
                monto_centavos=evento.costo_acordado_centavos,
                fecha=date.today(),
                cargo_id=atencion.cargo_id,
                usuario_id=usuario_id,
            )
            gasto_registrado = True
        else:
            if atencion_id is not None:
                atencion_opcional: Atencion | None = repository.obtener_atencion(
                    db, atencion_id
                )
                if (
                    atencion_opcional is None
                    or atencion_opcional.paciente_id != turno.paciente_id
                ):
                    raise AtencionTurnoNoEncontrada(
                        "La atención no existe o no corresponde al paciente del turno"
                    )
            turno.estado = EstadoTurno.ATENDIDO
            turno.atencion_id = atencion_id
    db.refresh(turno)
    return TurnoAtendidoOut(
        **_turno_out(turno).model_dump(),
        gasto_registrado=gasto_registrado,
    )


def turnos_de_paciente(db: Session, paciente_id: int) -> list[TurnoOut]:
    if padron_service.obtener_paciente(db, paciente_id) is None:
        raise PacienteTurnoNoEncontrado("El paciente no existe")
    return [
        _turno_out(item)
        for item in repository.listar_turnos(db, paciente_id=paciente_id)
    ]


def proximo_turno(db: Session, paciente_id: int) -> TurnoOut | None:
    if padron_service.obtener_paciente(db, paciente_id) is None:
        raise PacienteTurnoNoEncontrado("El paciente no existe")
    proximos = repository.listar_turnos(db, paciente_id=paciente_id)
    ahora = datetime.now()
    turno = next(
        (
            item
            for item in proximos
            if item.inicio >= ahora
            and item.estado
            in {
                EstadoTurno.PROGRAMADO,
                EstadoTurno.PENDIENTE_EXTERNO,
                EstadoTurno.CONFIRMADO,
            }
        ),
        None,
    )
    return _turno_out(turno) if turno is not None else None


def agenda(
    db: Session,
    desde: date,
    hasta: date,
    veterinario_id: int | None = None,
) -> list[AgendaDiaOut]:
    if desde > hasta:
        raise RangoAgendaInvalido("La fecha desde debe ser anterior o igual a hasta")

    horarios = repository.listar_horarios(db)
    turnos = repository.listar_turnos(
        db,
        desde=desde,
        hasta=hasta,
        veterinario_id=veterinario_id,
    )
    asignaciones = repository.listar_turnos_personal(db, desde=desde, hasta=hasta)
    horarios_por_dia: dict[int, list[HorarioAtencionOut]] = {}
    turnos_por_fecha: dict[date, list[TurnoOut]] = {}
    asignaciones_por_fecha: dict[date, list[TurnoPersonalOut]] = {}
    for horario in horarios:
        horarios_por_dia.setdefault(horario.dia_semana, []).append(
            _horario_out(horario)
        )
    for turno in turnos:
        turnos_por_fecha.setdefault(turno.inicio.date(), []).append(_turno_out(turno))
    for asignacion in asignaciones:
        asignaciones_por_fecha.setdefault(asignacion.fecha, []).append(
            _turno_personal_out(db, asignacion)
        )

    dias: list[AgendaDiaOut] = []
    dia = desde
    while dia <= hasta:
        dias.append(
            AgendaDiaOut(
                fecha=dia,
                horarios_atencion=horarios_por_dia.get(dia.weekday(), []),
                turnos=turnos_por_fecha.get(dia, []),
                turnos_personal=asignaciones_por_fecha.get(dia, []),
                ventanas_traspaso=ventanas_traspaso_del_dia(db, dia),
            )
        )
        dia += timedelta(days=1)
    return dias
