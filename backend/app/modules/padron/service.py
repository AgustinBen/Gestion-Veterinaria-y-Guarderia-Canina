"""Reglas de negocio del módulo padrón."""

from __future__ import annotations

import re
from datetime import date

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.padron import duplicados, models, normalizacion, repository, schemas


class DatosInvalidos(Exception):
    """Datos que no cumplen una regla de negocio."""


class PersonaNoEncontrada(Exception):
    """No existe la persona solicitada."""


class PacienteNoEncontrado(Exception):
    """No existe la mascota solicitada."""


class EmpleadoNoEncontrado(Exception):
    """No existe el empleado solicitado."""


class DniDuplicado(Exception):
    """El DNI ya existe; RN-02 bloquea el alta sin opción de confirmar."""

    def __init__(self, persona: schemas.PersonaResumen) -> None:
        super().__init__("El DNI ya está registrado")
        self.persona = persona


class PosibleDuplicado(Exception):
    """Hay teléfono repetido o nombre parecido; RN-06 exige confirmación."""

    def __init__(self, coincidencias: list[schemas.CoincidenciaOut]) -> None:
        super().__init__("Hay posibles duplicados")
        self.coincidencias = coincidencias


class TitularidadNoEncontrada(Exception):
    """No existe la titularidad pedida."""


class TitularidadConflicto(DatosInvalidos):
    """La operación dejaría la titularidad en un estado inválido (409)."""


def _mensaje_conflicto_integridad(exc: IntegrityError) -> str:
    detalle = str(exc.orig)
    if "titularidad.paciente_id, titularidad.persona_id" in detalle:
        return "La persona ya es titular vigente de la mascota"
    return "La operación dejaría dos principales vigentes"


def _texto_obligatorio(valor: str, campo: str) -> str:
    limpio = valor.strip()
    if not limpio:
        raise DatosInvalidos(f"El campo {campo} es obligatorio")
    return limpio


def _normalizar_telefonos(
    db: Session, telefonos: list[str], *, obligatorios: bool
) -> list[tuple[str, str]]:
    if obligatorios and not telefonos:
        raise DatosInvalidos("El teléfono es obligatorio")

    codigo_area = normalizacion.codigo_area_defecto(db)
    resultado: list[tuple[str, str]] = []
    vistos: set[str] = set()
    for original in telefonos:
        try:
            numero = normalizacion.normalizar_telefono(original, codigo_area)
        except normalizacion.TelefonoInvalido as exc:
            raise DatosInvalidos(str(exc)) from exc
        if numero in vistos:
            continue
        vistos.add(numero)
        resultado.append((numero, original))
    return resultado


def calcular_edad(
    fecha_nacimiento: date | None, hoy: date | None = None
) -> tuple[int | None, int | None]:
    """Edad calculada a partir de la fecha aproximada. Nunca se guarda (RN-09)."""
    if fecha_nacimiento is None:
        return None, None
    referencia = hoy or date.today()
    meses = (referencia.year - fecha_nacimiento.year) * 12 + (
        referencia.month - fecha_nacimiento.month
    )
    if referencia.day < fecha_nacimiento.day:
        meses -= 1
    if meses < 0:
        meses = 0
    return meses // 12, meses % 12


def _validar_domicilio(
    domicilio: schemas.DomicilioNuevo | None, *, migrado: bool = False
) -> None:
    """Desde la pantalla, calle y localidad son obligatorias (la migración queda exenta)."""
    if domicilio is None or migrado:
        return
    if not (domicilio.calle or "").strip():
        raise DatosInvalidos("La calle es obligatoria")
    if not (domicilio.localidad or "").strip():
        raise DatosInvalidos("La localidad es obligatoria")


def _resumen_persona(db: Session, persona: models.Persona) -> schemas.PersonaResumen:
    return schemas.PersonaResumen(
        id=persona.id,
        nombre=persona.nombre,
        apellido=persona.apellido,
        dni=persona.dni,
        dni_pendiente=persona.dni is None,
        telefonos=[
            telefono.numero_normalizado
            for telefono in repository.telefonos_de_persona(db, persona.id)
        ],
    )


def _resumen_paciente(
    db: Session, paciente: models.Paciente
) -> schemas.PacienteResumen:
    especie = repository.obtener_especie(db, paciente.especie_id)
    raza = (
        repository.obtener_raza(db, paciente.raza_id)
        if paciente.raza_id is not None
        else None
    )
    return schemas.PacienteResumen(
        id=paciente.id,
        nombre=paciente.nombre,
        especie_id=paciente.especie_id,
        especie_nombre=especie.nombre if especie else "",
        raza_id=paciente.raza_id,
        raza_nombre=raza.nombre if raza else None,
        activo=paciente.activo,
    )


def _detalle_persona(db: Session, persona: models.Persona) -> schemas.PersonaDetalle:
    domicilio = (
        db.get(models.Domicilio, persona.domicilio_id)
        if persona.domicilio_id is not None
        else None
    )
    return schemas.PersonaDetalle(
        id=persona.id,
        nombre=persona.nombre,
        apellido=persona.apellido,
        dni=persona.dni,
        dni_pendiente=persona.dni is None,
        domicilio=(
            schemas.DomicilioOut.model_validate(domicilio) if domicilio else None
        ),
        telefonos=[
            telefono.numero_normalizado
            for telefono in repository.telefonos_de_persona(db, persona.id)
        ],
        creado_en=persona.creado_en,
        duplicado_confirmado=persona.duplicado_confirmado,
        mascotas=[
            _resumen_paciente(db, paciente)
            for paciente in repository.mascotas_de_persona(db, persona.id)
        ],
    )


def _detalle_paciente(
    db: Session, paciente: models.Paciente
) -> schemas.PacienteDetalle:
    return _detalle_pacientes(db, [paciente])[paciente.id]


def _detalle_pacientes(
    db: Session,
    pacientes: list[models.Paciente],
) -> dict[int, schemas.PacienteDetalle]:
    if not pacientes:
        return {}

    especies = repository.obtener_especies_por_ids(
        db, list({paciente.especie_id for paciente in pacientes})
    )
    razas = repository.obtener_razas_por_ids(
        db,
        [paciente.raza_id for paciente in pacientes if paciente.raza_id is not None],
    )
    tamanios = repository.obtener_tamanios_por_ids(
        db,
        [
            paciente.tamanio_id
            for paciente in pacientes
            if paciente.tamanio_id is not None
        ],
    )
    detalles: dict[int, schemas.PacienteDetalle] = {}
    for paciente in pacientes:
        especie = especies.get(paciente.especie_id)
        raza = razas.get(paciente.raza_id) if paciente.raza_id is not None else None
        tamanio = (
            tamanios.get(paciente.tamanio_id)
            if paciente.tamanio_id is not None
            else None
        )
        edad_anios, edad_meses = calcular_edad(paciente.fecha_nacimiento_aprox)
        detalles[paciente.id] = schemas.PacienteDetalle(
            id=paciente.id,
            nombre=paciente.nombre,
            especie_id=paciente.especie_id,
            especie_nombre=especie.nombre if especie else "",
            raza_id=paciente.raza_id,
            raza_nombre=raza.nombre if raza else None,
            tamanio_id=paciente.tamanio_id,
            tamanio_nombre=tamanio.nombre if tamanio else None,
            peso_kg=paciente.peso_kg,  # type: ignore[arg-type]
            fecha_nacimiento_aprox=paciente.fecha_nacimiento_aprox,
            castrado=paciente.castrado,
            activo=paciente.activo,
            edad_anios=edad_anios,
            edad_meses=edad_meses,
        )
    return detalles


def _detalle_empleado(
    db: Session, empleado: models.Empleado, persona: models.Persona
) -> schemas.EmpleadoDetalle:
    return schemas.EmpleadoDetalle(
        persona_id=empleado.persona_id,
        nombre=persona.nombre,
        apellido=persona.apellido,
        dni=persona.dni,
        dni_pendiente=persona.dni is None,
        telefonos=[
            telefono.numero_normalizado
            for telefono in repository.telefonos_de_persona(db, empleado.persona_id)
        ],
        tipo=empleado.tipo,
        es_veterinario=empleado.es_veterinario,
        especialidad=empleado.especialidad,
        email=empleado.email,
        activo=empleado.activo,
    )


def _coincidencias_out(
    db: Session, coincidencias: list[duplicados.Coincidencia]
) -> list[schemas.CoincidenciaOut]:
    return [
        duplicados.a_coincidencia_out(db, coincidencia)
        for coincidencia in coincidencias
    ]


def _puntaje_persona(db: Session, persona: models.Persona, texto: str) -> int:
    normalizado = normalizacion.normalizar_texto(texto)
    digitos = re.sub(r"\D", "", texto)
    if len(digitos) > 10:
        digitos = digitos[-10:]
    puntaje = 0

    if digitos and persona.dni:
        if persona.dni == digitos:
            puntaje += 100
        elif digitos in persona.dni:
            puntaje += 90

    apellido = normalizacion.normalizar_texto(persona.apellido)
    nombre = normalizacion.normalizar_texto(persona.nombre)
    completo = normalizacion.normalizar_texto(f"{persona.nombre} {persona.apellido}")
    if normalizado and apellido == normalizado:
        puntaje += 80
    if normalizado and nombre == normalizado:
        puntaje += 70
    if normalizado and completo.startswith(normalizado):
        puntaje += 60
    if normalizado and normalizado in completo:
        puntaje += 50

    if digitos:
        for telefono in repository.telefonos_de_persona(db, persona.id):
            if digitos in telefono.numero_normalizado:
                puntaje += 40
                break

    if normalizado:
        for paciente in repository.mascotas_de_persona(db, persona.id):
            if normalizado in normalizacion.normalizar_texto(paciente.nombre):
                puntaje += 30
                break

    return puntaje


def buscar_personas(
    db: Session,
    texto: str | None = None,
    dni: str | None = None,
    telefono: str | None = None,
    limite: int = 20,
    offset: int = 0,
) -> list[schemas.PersonaResumen]:
    """Búsqueda libre y paginada, ordenada por relevancia."""
    dni_normalizado = normalizacion.normalizar_dni(dni)
    telefono_normalizado: str | None = None
    if telefono:
        try:
            telefono_normalizado = normalizacion.normalizar_telefono(
                telefono, normalizacion.codigo_area_defecto(db)
            )
        except normalizacion.TelefonoInvalido as exc:
            raise DatosInvalidos(str(exc)) from exc

    personas = repository.buscar_personas(
        db, texto=texto, dni=dni_normalizado, telefono=telefono_normalizado
    )
    if texto:
        personas.sort(
            key=lambda persona: (
                -_puntaje_persona(db, persona, texto),
                normalizacion.normalizar_texto(persona.apellido),
                normalizacion.normalizar_texto(persona.nombre),
                persona.id,
            )
        )
    else:
        personas.sort(
            key=lambda persona: (
                normalizacion.normalizar_texto(persona.apellido),
                normalizacion.normalizar_texto(persona.nombre),
                persona.id,
            )
        )

    limite = max(1, limite)
    offset = max(0, offset)
    pagina = personas[offset : offset + limite]
    return [_resumen_persona(db, persona) for persona in pagina]


def obtener_persona(db: Session, persona_id: int) -> schemas.PersonaDetalle | None:
    persona = repository.obtener_persona(db, persona_id)
    if persona is None:
        return None
    return _detalle_persona(db, persona)


def obtener_personas_resumen(
    db: Session, ids: list[int]
) -> dict[int, schemas.PersonaResumen]:
    personas = repository.obtener_personas_por_ids(db, ids)
    telefonos = repository.obtener_telefonos_por_ids(
        db, [persona.id for persona in personas]
    )
    return {
        persona.id: schemas.PersonaResumen(
            id=persona.id,
            nombre=persona.nombre,
            apellido=persona.apellido,
            dni=persona.dni,
            dni_pendiente=persona.dni is None,
            telefonos=telefonos.get(persona.id, []),
        )
        for persona in personas
    }


def pacientes_de_persona(
    db: Session, persona_id: int
) -> list[schemas.PacienteResumen]:
    return [
        _resumen_paciente(db, paciente)
        for paciente in repository.mascotas_de_persona(db, persona_id)
    ]


def obtener_paciente(db: Session, paciente_id: int) -> schemas.PacienteDetalle | None:
    paciente = repository.obtener_paciente(db, paciente_id)
    if paciente is None:
        return None
    return _detalle_paciente(db, paciente)


def obtener_pacientes(
    db: Session, ids: list[int]
) -> dict[int, schemas.PacienteDetalle]:
    """Obtiene varias fichas de paciente con consultas agrupadas por catálogo."""
    pacientes = repository.obtener_pacientes_por_ids(db, sorted(set(ids)))
    return _detalle_pacientes(db, pacientes)


def buscar_pacientes(
    db: Session,
    texto: str | None = None,
    limite: int = 20,
    offset: int = 0,
) -> list[schemas.PacienteResumen]:
    """Búsqueda paginada de mascotas por nombre o por datos de su titular."""
    pacientes = repository.buscar_pacientes(db, texto=texto)
    limite = max(1, limite)
    offset = max(0, offset)
    return [
        _resumen_paciente(db, paciente)
        for paciente in pacientes[offset : offset + limite]
    ]


def _paciente_o_error(db: Session, paciente_id: int) -> models.Paciente:
    paciente = repository.obtener_paciente(db, paciente_id)
    if paciente is None:
        raise PacienteNoEncontrado()
    return paciente


def _tipo_contacto_o_error(
    db: Session,
    tipo_contacto_id: int | None,
    *,
    defecto: str | None = "TITULAR",
) -> models.TipoContacto:
    if tipo_contacto_id is None:
        if defecto is None:
            raise DatosInvalidos("Falta el tipo de contacto")
        tipo = repository.obtener_tipo_contacto_por_nombre(db, defecto)
        if tipo is None:
            raise DatosInvalidos(f"Falta el tipo de contacto {defecto} en el catálogo")
        return tipo
    tipo = db.get(models.TipoContacto, tipo_contacto_id)
    if tipo is None:
        raise DatosInvalidos("El tipo de contacto no existe")
    return tipo


def _titular_out(db: Session, titularidad: models.Titularidad) -> schemas.TitularVigente:
    persona = repository.obtener_persona(db, titularidad.persona_id)
    if persona is None:
        raise PersonaNoEncontrada()
    tipo = db.get(models.TipoContacto, titularidad.tipo_contacto_id)
    if tipo is None:
        raise DatosInvalidos("El tipo de contacto no existe")
    return schemas.TitularVigente(
        id=titularidad.id,
        persona_id=persona.id,
        nombre=persona.nombre,
        apellido=persona.apellido,
        tipo=tipo.nombre,
        principal=titularidad.principal,
        desde=titularidad.desde,
        hasta=titularidad.hasta,
    )


def titulares_vigentes(db: Session, paciente_id: int) -> list[schemas.TitularVigente]:
    return [
        _titular_out(db, titularidad)
        for titularidad in repository.titulares_vigentes(db, paciente_id)
    ]


def titulares_historial(db: Session, paciente_id: int) -> list[schemas.TitularVigente]:
    """Todas las titularidades del paciente, incluidas las cerradas (T-13)."""
    return [
        _titular_out(db, titularidad)
        for titularidad in repository.titulares_historial(db, paciente_id)
    ]


# La titularidad no guarda auditoría en la spec de padrón; ``usuario_id`` se
# acepta para no romper el contrato del ticket, pero no se persiste.
def agregar_titular(
    db: Session,
    paciente_id: int,
    persona_id: int,
    tipo_contacto_id: int | None = None,
    *,
    principal: bool = False,
    usuario_id: int | None = None,
    fecha: date | None = None,
) -> schemas.TitularVigente:
    """Agrega un titular vigente. La primera titularidad es siempre principal."""
    _paciente_o_error(db, paciente_id)
    if repository.obtener_persona(db, persona_id) is None:
        raise PersonaNoEncontrada()

    tipo = _tipo_contacto_o_error(db, tipo_contacto_id)
    vigentes = repository.titulares_vigentes(db, paciente_id)
    if any(titular.persona_id == persona_id for titular in vigentes):
        raise TitularidadConflicto("La persona ya es titular vigente de la mascota")

    actual_principal: models.Titularidad | None = None
    if not vigentes:
        if tipo.nombre != "TITULAR":
            raise DatosInvalidos("La primera titularidad debe ser TITULAR")
        es_principal = True
    elif principal:
        if tipo.nombre != "TITULAR":
            raise DatosInvalidos("Solo un TITULAR puede ser principal")
        actual_principal = next(
            (titular for titular in vigentes if titular.principal), None
        )
        es_principal = True
    else:
        es_principal = False

    titularidad = models.Titularidad(
        paciente_id=paciente_id,
        persona_id=persona_id,
        tipo_contacto_id=tipo.id,
        principal=es_principal,
        desde=fecha or date.today(),
    )
    try:
        if actual_principal is not None:
            actual_principal.principal = False
            db.flush()
        repository.crear_titularidad(db, titularidad)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise TitularidadConflicto(_mensaje_conflicto_integridad(exc)) from exc
    except Exception:
        db.rollback()
        raise

    return _titular_out(db, titularidad)


def quitar_titular(
    db: Session,
    titularidad_id: int,
    *,
    usuario_id: int | None = None,
    fecha: date | None = None,
) -> None:
    """Cierra la vigencia (nunca borra). No permite dejar la mascota sin titular."""
    titularidad = repository.obtener_titularidad(db, titularidad_id)
    if titularidad is None:
        raise TitularidadNoEncontrada()
    if titularidad.hasta is not None:
        raise TitularidadConflicto("La titularidad ya está cerrada")

    vigentes = repository.titulares_vigentes(db, titularidad.paciente_id)
    if len(vigentes) <= 1:
        raise TitularidadConflicto(
            "No se puede quitar al único titular vigente de la mascota"
        )
    if titularidad.principal:
        raise TitularidadConflicto(
            "Antes de quitar al titular principal, designá otro principal"
        )

    fin = fecha or date.today()
    if fin < titularidad.desde:
        raise DatosInvalidos("La fecha de cierre no puede ser anterior al alta")
    titularidad.hasta = fin
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


def quitar_titular_de_persona(
    db: Session,
    paciente_id: int,
    persona_id: int,
    *,
    usuario_id: int | None = None,
    fecha: date | None = None,
) -> None:
    for titularidad in repository.titulares_vigentes(db, paciente_id):
        if titularidad.persona_id == persona_id:
            quitar_titular(
                db, titularidad.id, usuario_id=usuario_id, fecha=fecha
            )
            return
    raise TitularidadNoEncontrada()


def cambiar_principal(
    db: Session,
    paciente_id: int,
    persona_id: int,
    *,
    usuario_id: int | None = None,
) -> schemas.TitularVigente:
    """Deja exactamente un principal vigente, sin sacar a los demás titulares."""
    _paciente_o_error(db, paciente_id)
    vigentes = repository.titulares_vigentes(db, paciente_id)
    objetivo = next(
        (titular for titular in vigentes if titular.persona_id == persona_id), None
    )
    if objetivo is None:
        raise TitularidadConflicto(
            "La persona no es titular vigente de la mascota"
        )
    tipo = _tipo_contacto_o_error(db, objetivo.tipo_contacto_id, defecto=None)
    if tipo.nombre != "TITULAR":
        raise DatosInvalidos("Solo un TITULAR puede ser principal")
    if objetivo.principal:
        return _titular_out(db, objetivo)

    try:
        for titular in vigentes:
            if titular.principal:
                titular.principal = False
                db.flush()
        objetivo.principal = True
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise TitularidadConflicto(_mensaje_conflicto_integridad(exc)) from exc
    except Exception:
        db.rollback()
        raise

    return _titular_out(db, objetivo)


def transferir_paciente(
    db: Session,
    paciente_id: int,
    nueva_persona_id: int,
    fecha: date | None = None,
    *,
    de_persona_id: int | None = None,
    tipo_contacto_id: int | None = None,
    usuario_id: int | None = None,
) -> schemas.TitularVigente:
    """Cierra la titularidad saliente y abre la nueva en una sola transacción."""
    _paciente_o_error(db, paciente_id)
    if repository.obtener_persona(db, nueva_persona_id) is None:
        raise PersonaNoEncontrada()

    vigentes = repository.titulares_vigentes(db, paciente_id)
    if de_persona_id is None:
        saliente = next(
            (titular for titular in vigentes if titular.principal), None
        )
        if saliente is None and len(vigentes) == 1:
            saliente = vigentes[0]
        if saliente is None:
            raise TitularidadConflicto(
                "Indicá qué titular sale: hay más de uno y ninguno es principal"
            )
    else:
        saliente = next(
            (
                titular
                for titular in vigentes
                if titular.persona_id == de_persona_id
            ),
            None,
        )
        if saliente is None:
            raise TitularidadConflicto(
                "La persona que sale no es titular vigente de la mascota"
            )

    if saliente.persona_id == nueva_persona_id:
        raise TitularidadConflicto("La persona que sale y la que entra son la misma")
    if any(titular.persona_id == nueva_persona_id for titular in vigentes):
        raise TitularidadConflicto(
            "La persona que entra ya es titular vigente de la mascota"
        )

    if tipo_contacto_id is None:
        tipo = _tipo_contacto_o_error(
            db, saliente.tipo_contacto_id, defecto=None
        )
    else:
        tipo = _tipo_contacto_o_error(db, tipo_contacto_id)

    queda_principal = any(
        titular.principal
        for titular in vigentes
        if titular.id != saliente.id
    )
    nuevo_principal = saliente.principal or not queda_principal
    if nuevo_principal and tipo.nombre != "TITULAR":
        raise DatosInvalidos("Un principal debe ser TITULAR")

    fin = fecha or date.today()
    if fin < saliente.desde:
        raise DatosInvalidos("La fecha de transferencia no puede ser anterior al alta")

    nueva = models.Titularidad(
        paciente_id=paciente_id,
        persona_id=nueva_persona_id,
        tipo_contacto_id=tipo.id,
        principal=nuevo_principal,
        desde=fin,
    )
    try:
        saliente.hasta = fin
        db.flush()
        repository.crear_titularidad(db, nueva)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise TitularidadConflicto(_mensaje_conflicto_integridad(exc)) from exc
    except Exception:
        db.rollback()
        raise

    return _titular_out(db, nueva)


def obtener_empleado(db: Session, empleado_id: int) -> schemas.EmpleadoDetalle | None:
    empleado = repository.obtener_empleado(db, empleado_id)
    if empleado is None:
        return None
    persona = repository.obtener_persona(db, empleado.persona_id)
    if persona is None:
        return None
    return _detalle_empleado(db, empleado, persona)


def crear_persona(
    db: Session,
    datos: schemas.PersonaNueva,
    *,
    confirmar_duplicado: bool | None = None,
    migrado: bool = False,
    creado_por: int | None = None,
) -> schemas.PersonaDetalle:
    """Alta de persona con control de duplicados.

    ``migrado=True`` permite omitir DNI y teléfono (RN-02 y RN-50). El DNI
    repetido nunca se confirma; el teléfono o nombre repetido solo con
    ``confirmar_duplicado=True``.
    """
    confirmar = (
        datos.confirmar_duplicado
        if confirmar_duplicado is None
        else confirmar_duplicado
    )
    nombre = normalizacion.formatear_nombre(
        _texto_obligatorio(datos.nombre, "nombre")
    )
    apellido = normalizacion.formatear_nombre(
        _texto_obligatorio(datos.apellido, "apellido")
    )
    dni = normalizacion.normalizar_dni(datos.dni)
    if dni is None and not migrado:
        raise DatosInvalidos("El DNI es obligatorio")

    if dni is not None:
        existente = repository.obtener_por_dni(db, dni)
        if existente is not None:
            raise DniDuplicado(_resumen_persona(db, existente))

    telefonos = _normalizar_telefonos(db, datos.telefonos, obligatorios=not migrado)
    _validar_domicilio(datos.domicilio, migrado=migrado)

    if confirmar:
        if datos.persona_coincidente_id is not None:
            if repository.obtener_persona(db, datos.persona_coincidente_id) is None:
                raise DatosInvalidos("La persona coincidente no existe")
    else:
        coincidencias = duplicados.detectar_coincidencias(
            db,
            nombre,
            apellido,
            [numero for numero, _ in telefonos],
            normalizacion.umbral_nombre_parecido(db),
        )
        if coincidencias:
            raise PosibleDuplicado(_coincidencias_out(db, coincidencias))

    domicilio_id: int | None = None
    if datos.domicilio is not None:
        domicilio = repository.crear_domicilio(
            db, models.Domicilio(**datos.domicilio.model_dump())
        )
        domicilio_id = domicilio.id

    persona = models.Persona(
        nombre=nombre,
        apellido=apellido,
        dni=dni,
        domicilio_id=domicilio_id,
        creado_por=creado_por,
        duplicado_confirmado=confirmar,
    )
    repository.crear_persona(db, persona)
    for numero, original in telefonos:
        repository.crear_telefono(
            db,
            models.Telefono(
                persona_id=persona.id,
                numero_normalizado=numero,
                numero_original=original,
            ),
        )

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if dni is not None:
            existente = repository.obtener_por_dni(db, dni)
            if existente is not None:
                raise DniDuplicado(_resumen_persona(db, existente)) from exc
        raise

    db.refresh(persona)
    return _detalle_persona(db, persona)


def actualizar_persona(
    db: Session, persona_id: int, datos: schemas.PersonaActualizar
) -> schemas.PersonaDetalle:
    persona = repository.obtener_persona(db, persona_id)
    if persona is None:
        raise PersonaNoEncontrada()

    campos = datos.model_fields_set
    if not campos:
        raise DatosInvalidos("No hay campos para actualizar")

    nombre = persona.nombre
    if "nombre" in campos:
        if datos.nombre is None:
            raise DatosInvalidos("El nombre no puede ser nulo")
        nombre = normalizacion.formatear_nombre(
            _texto_obligatorio(datos.nombre, "nombre")
        )

    apellido = persona.apellido
    if "apellido" in campos:
        if datos.apellido is None:
            raise DatosInvalidos("El apellido no puede ser nulo")
        apellido = normalizacion.formatear_nombre(
            _texto_obligatorio(datos.apellido, "apellido")
        )

    dni = persona.dni
    if "dni" in campos:
        dni = normalizacion.normalizar_dni(datos.dni)
        if dni is None:
            raise DatosInvalidos("El DNI es obligatorio")
        existente = repository.obtener_por_dni(db, dni, excluir_id=persona.id)
        if existente is not None:
            raise DniDuplicado(_resumen_persona(db, existente))

    nuevos_telefonos: list[tuple[str, str]] | None = None
    if "telefonos" in campos:
        if datos.telefonos is None:
            raise DatosInvalidos("La lista de teléfonos no puede ser nula")
        nuevos_telefonos = _normalizar_telefonos(
            db, datos.telefonos, obligatorios=True
        )

    cambio_sensible = any(
        campo in campos for campo in ("nombre", "apellido", "telefonos")
    )
    if cambio_sensible and not datos.confirmar_duplicado:
        if nuevos_telefonos is not None:
            numeros = [numero for numero, _ in nuevos_telefonos]
        else:
            numeros = [
                telefono.numero_normalizado
                for telefono in repository.telefonos_de_persona(db, persona.id)
            ]
        coincidencias = duplicados.detectar_coincidencias(
            db,
            nombre,
            apellido,
            numeros,
            normalizacion.umbral_nombre_parecido(db),
            excluir_id=persona.id,
        )
        if coincidencias:
            raise PosibleDuplicado(_coincidencias_out(db, coincidencias))

    if datos.confirmar_duplicado:
        persona.duplicado_confirmado = True

    persona.nombre = nombre
    persona.apellido = apellido
    persona.dni = dni

    if "domicilio" in campos:
        _validar_domicilio(datos.domicilio)
        if datos.domicilio is None:
            persona.domicilio_id = None
        elif persona.domicilio_id is None:
            domicilio = repository.crear_domicilio(
                db, models.Domicilio(**datos.domicilio.model_dump())
            )
            persona.domicilio_id = domicilio.id
        else:
            actual = db.get(models.Domicilio, persona.domicilio_id)
            if actual is None:
                domicilio = repository.crear_domicilio(
                    db, models.Domicilio(**datos.domicilio.model_dump())
                )
                persona.domicilio_id = domicilio.id
            else:
                repository.actualizar_domicilio(
                    db, actual, datos.domicilio.model_dump()
                )

    if nuevos_telefonos is not None:
        repository.reemplazar_telefonos(db, persona.id, nuevos_telefonos)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if dni is not None:
            existente = repository.obtener_por_dni(db, dni, excluir_id=persona.id)
            if existente is not None:
                raise DniDuplicado(_resumen_persona(db, existente)) from exc
        raise

    db.refresh(persona)
    return _detalle_persona(db, persona)


def reemplazar_telefonos(
    db: Session, persona_id: int, datos: schemas.TelefonosUpdate
) -> schemas.PersonaDetalle:
    return actualizar_persona(
        db,
        persona_id,
        schemas.PersonaActualizar(
            telefonos=datos.telefonos,
            confirmar_duplicado=datos.confirmar_duplicado,
            persona_coincidente_id=datos.persona_coincidente_id,
        ),
    )


def crear_paciente(
    db: Session,
    datos: schemas.PacienteNuevo,
    titular_persona_id: int | None = None,
) -> schemas.PacienteDetalle:
    titular_id = (
        titular_persona_id
        if titular_persona_id is not None
        else datos.titular_persona_id
    )
    if repository.obtener_persona(db, titular_id) is None:
        raise DatosInvalidos("El titular no existe")

    especie = repository.obtener_especie(db, datos.especie_id)
    if especie is None:
        raise DatosInvalidos("La especie no existe")

    if datos.raza_id is not None:
        raza = repository.obtener_raza(db, datos.raza_id)
        if raza is None or raza.especie_id != especie.id:
            raise DatosInvalidos("La raza no corresponde a la especie")

    if datos.tamanio_id is not None:
        if repository.obtener_tamanio(db, datos.tamanio_id) is None:
            raise DatosInvalidos("El tamaño no existe")

    tipo_titular = repository.obtener_tipo_contacto_por_nombre(db, "TITULAR")
    if tipo_titular is None:
        raise DatosInvalidos("Falta el tipo de contacto TITULAR en el catálogo")

    paciente = models.Paciente(
        nombre=_texto_obligatorio(datos.nombre, "nombre"),
        especie_id=datos.especie_id,
        raza_id=datos.raza_id,
        tamanio_id=datos.tamanio_id,
        peso_kg=datos.peso_kg,
        fecha_nacimiento_aprox=datos.fecha_nacimiento_aprox,
        castrado=datos.castrado,
    )
    repository.crear_paciente(db, paciente)
    repository.crear_titularidad(
        db,
        models.Titularidad(
            paciente_id=paciente.id,
            persona_id=titular_id,
            tipo_contacto_id=tipo_titular.id,
            principal=True,
            desde=date.today(),
        ),
    )
    db.commit()
    db.refresh(paciente)
    return _detalle_paciente(db, paciente)


def actualizar_paciente(
    db: Session, paciente_id: int, datos: schemas.PacienteActualizar
) -> schemas.PacienteDetalle:
    paciente = repository.obtener_paciente(db, paciente_id)
    if paciente is None:
        raise PacienteNoEncontrado()

    campos = datos.model_fields_set
    if not campos:
        raise DatosInvalidos("No hay campos para actualizar")

    if "nombre" in campos:
        if datos.nombre is None:
            raise DatosInvalidos("El nombre no puede ser nulo")
        paciente.nombre = _texto_obligatorio(datos.nombre, "nombre")

    if "especie_id" in campos:
        if datos.especie_id is None:
            raise DatosInvalidos("La especie es obligatoria")
        if repository.obtener_especie(db, datos.especie_id) is None:
            raise DatosInvalidos("La especie no existe")
        paciente.especie_id = datos.especie_id

    if "raza_id" in campos:
        if datos.raza_id is not None:
            raza = repository.obtener_raza(db, datos.raza_id)
            if raza is None or raza.especie_id != paciente.especie_id:
                raise DatosInvalidos("La raza no corresponde a la especie")
        paciente.raza_id = datos.raza_id

    if "tamanio_id" in campos:
        if datos.tamanio_id is not None:
            if repository.obtener_tamanio(db, datos.tamanio_id) is None:
                raise DatosInvalidos("El tamaño no existe")
        paciente.tamanio_id = datos.tamanio_id

    if "peso_kg" in campos:
        paciente.peso_kg = datos.peso_kg  # type: ignore[assignment]
    if "fecha_nacimiento_aprox" in campos:
        paciente.fecha_nacimiento_aprox = datos.fecha_nacimiento_aprox
    if "castrado" in campos:
        paciente.castrado = datos.castrado
    if "activo" in campos:
        if datos.activo is None:
            raise DatosInvalidos("El campo activo no puede ser nulo")
        paciente.activo = datos.activo

    db.commit()
    db.refresh(paciente)
    return _detalle_paciente(db, paciente)


def listar_empleados(db: Session) -> list[schemas.EmpleadoDetalle]:
    resultado: list[schemas.EmpleadoDetalle] = []
    for empleado in repository.listar_empleados(db):
        persona = repository.obtener_persona(db, empleado.persona_id)
        if persona is None:
            continue
        resultado.append(_detalle_empleado(db, empleado, persona))
    return resultado


def crear_empleado(
    db: Session, datos: schemas.EmpleadoNuevo, *, creado_por: int | None = None
) -> schemas.EmpleadoDetalle:
    persona = crear_persona(db, datos.persona, creado_por=creado_por)
    empleado = models.Empleado(
        persona_id=persona.id,
        tipo=datos.tipo,
        es_veterinario=datos.es_veterinario,
        especialidad=datos.especialidad,
        email=datos.email,
        activo=datos.activo,
    )
    repository.crear_empleado(db, empleado)
    db.commit()
    db.refresh(empleado)
    return _detalle_empleado(db, empleado, repository.obtener_persona(db, persona.id))  # type: ignore[arg-type]


def actualizar_empleado(
    db: Session, empleado_id: int, datos: schemas.EmpleadoActualizar
) -> schemas.EmpleadoDetalle:
    empleado = repository.obtener_empleado(db, empleado_id)
    if empleado is None:
        raise EmpleadoNoEncontrado()

    campos = datos.model_fields_set
    if not campos:
        raise DatosInvalidos("No hay campos para actualizar")

    if "tipo" in campos:
        if datos.tipo is None:
            raise DatosInvalidos("El tipo no puede ser nulo")
        empleado.tipo = datos.tipo
    if "es_veterinario" in campos:
        if datos.es_veterinario is None:
            raise DatosInvalidos("es_veterinario no puede ser nulo")
        empleado.es_veterinario = datos.es_veterinario
    if "especialidad" in campos:
        empleado.especialidad = datos.especialidad
    if "email" in campos:
        empleado.email = datos.email
    if "activo" in campos:
        if datos.activo is None:
            raise DatosInvalidos("El campo activo no puede ser nulo")
        empleado.activo = datos.activo

    db.commit()
    db.refresh(empleado)
    persona = repository.obtener_persona(db, empleado.persona_id)
    if persona is None:
        raise EmpleadoNoEncontrado()
    return _detalle_empleado(db, empleado, persona)


def listar_especies(db: Session) -> list[schemas.EspecieOut]:
    return [
        schemas.EspecieOut.model_validate(especie)
        for especie in repository.listar_especies(db)
    ]


def listar_razas(db: Session, especie_id: int | None = None) -> list[schemas.RazaOut]:
    return [
        schemas.RazaOut.model_validate(raza)
        for raza in repository.listar_razas(db, especie_id)
    ]


def listar_tamanios(db: Session) -> list[schemas.TamanioOut]:
    return [
        schemas.TamanioOut.model_validate(tamanio)
        for tamanio in repository.listar_tamanios(db)
    ]


def crear_raza(db: Session, datos: schemas.RazaNueva) -> schemas.RazaOut:
    """Alta rápida idempotente por nombre normalizado y especie."""
    especie = repository.obtener_especie(db, datos.especie_id)
    if especie is None:
        raise DatosInvalidos("La especie no existe")

    nombre = normalizacion.formatear_nombre(
        _texto_obligatorio(datos.nombre, "nombre")
    )
    for raza in repository.listar_razas(db, especie_id=especie.id):
        if normalizacion.normalizar_texto(raza.nombre) == normalizacion.normalizar_texto(
            nombre
        ):
            return schemas.RazaOut.model_validate(raza)

    nueva = repository.crear_raza(
        db, models.Raza(nombre=nombre, especie_id=especie.id)
    )
    db.commit()
    db.refresh(nueva)
    return schemas.RazaOut.model_validate(nueva)
