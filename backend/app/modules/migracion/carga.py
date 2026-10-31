"""Carga idempotente de la hoja Clientes_y_Mascotas (T-16, RN-02, RN-06, RN-50).

Cada fila se procesa en su propia transacción: persona, mascota, titularidad y
registro de migración caen juntos o no cae ninguno. Solo se escribe a través de
``padron.service``. La edad se convierte en fecha aproximada (RN-09), la especie
nunca se asume (RN-05) y ningún duplicado se fusiona solo (RN-06).
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session

from app.core import parametros
from app.core.parametros import ParametroNoDefinido
from app.modules.migracion import normalizacion, repository
from app.modules.migracion.lector import FilaCruda, leer_libro
from app.modules.migracion.models import (
    ESTADO_CARGADA,
    ESTADO_ERROR,
    ESTADO_REVISION,
    HOJA_CLIENTES,
    MigracionRegistro,
)
from app.modules.migracion.normalizacion import (
    REVISION,
    SIN_TELEFONO,
    clave_comparable,
    claves_de_comparacion,
    edad_a_meses,
    especie_raza,
    fecha_nacimiento_aprox,
    limpiar_nombre_dueno,
    peso_kg,
    telefono,
)
from app.modules.migracion.revision import FilaRevision, escribir_revision, ruta_revision
from app.modules.migracion.seed import CLAVE_FECHA_CORTE, CLAVE_PESO_MAX_KG
from app.modules.padron import schemas as padron_schemas
from app.modules.padron import service as padron_service
from app.modules.padron.service import DatosInvalidos, DniDuplicado, PosibleDuplicado

HOJA = HOJA_CLIENTES
ENTIDAD_PACIENTE = "PACIENTE"
# Límite de lectura de candidatos de padrón; no es una regla de negocio.
LIMITE_BUSQUEDA = 200
NOMBRE_REPORTE = "reporte_carga.json"


class ErrorParametroMigracion(ValueError):
    """Un parámetro de migración existe pero no tiene un valor usable."""


@dataclass(frozen=True)
class ConflictoPeso:
    paciente_id: int
    fila_anterior: int
    fila_nueva: int
    peso_anterior: str
    peso_nuevo: str


@dataclass
class ReporteCarga:
    simulacion: bool = False
    leidas: int = 0
    cargadas: int = 0
    ya_cargadas: int = 0
    cambiadas: int = 0
    mascotas_existentes: int = 0
    errores: int = 0
    a_revision: Counter[str] = field(default_factory=Counter)
    conflictos_peso: list[ConflictoPeso] = field(default_factory=list)

    def a_dict(self) -> dict[str, Any]:
        return {
            "simulacion": self.simulacion,
            "hoja": HOJA,
            "leidas": self.leidas,
            "cargadas": self.cargadas,
            "ya_cargadas": self.ya_cargadas,
            "cambiadas": self.cambiadas,
            "mascotas_existentes": self.mascotas_existentes,
            "a_revision": dict(sorted(self.a_revision.items())),
            "conflictos_peso": [
                {
                    "paciente_id": conflicto.paciente_id,
                    "fila_anterior": conflicto.fila_anterior,
                    "fila_nueva": conflicto.fila_nueva,
                    "peso_anterior": conflicto.peso_anterior,
                    "peso_nuevo": conflicto.peso_nuevo,
                }
                for conflicto in self.conflictos_peso
            ],
            "errores": self.errores,
        }


@dataclass(frozen=True)
class _ResultadoFila:
    estado: str
    motivo: str | None = None
    campo: str = ""
    valor_original: str = ""
    accion: str = ""
    entidad: str | None = None
    entidad_id: int | None = None
    mascota_existente: bool = False
    conflicto: ConflictoPeso | None = None


def resumen_consola(reporte: ReporteCarga) -> str:
    """Resumen sin datos personales: solo conteos."""
    lineas = [
        "Simulación: no se escribió en la base de datos."
        if reporte.simulacion
        else "Carga completada.",
        f"Filas leídas: {reporte.leidas}",
        f"Cargadas: {reporte.cargadas}",
        f"Ya cargadas (se saltearon): {reporte.ya_cargadas}",
        f"Cambiadas (no se pisaron): {reporte.cambiadas}",
        f"Mascotas ya existentes: {reporte.mascotas_existentes}",
        f"A revisión: {sum(reporte.a_revision.values())}",
        f"Errores: {reporte.errores}",
    ]
    if reporte.a_revision:
        detalle = ", ".join(
            f"{motivo}={cantidad}"
            for motivo, cantidad in sorted(reporte.a_revision.items())
        )
        lineas.append(f"Revisión por motivo: {detalle}")
    if reporte.conflictos_peso:
        lineas.append(f"Conflictos de peso: {len(reporte.conflictos_peso)}")
    return "\n".join(lineas)


def escribir_reporte(reporte: ReporteCarga, salida: Path) -> Path:
    salida.mkdir(parents=True, exist_ok=True)
    destino = salida / NOMBRE_REPORTE
    destino.write_text(
        json.dumps(reporte.a_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return destino


@contextmanager
def _sesion_fila(engine: Engine, conexion: Connection | None) -> Iterator[Session]:
    """Sesión con savepoint: los ``commit()`` del service no cierran la fila.

    Con ``conexion`` (simulación) la transacción externa es única para toda la
    corrida y se revierte al final. Sin ``conexion`` (carga real) cada fila abre
    su propia conexión y su propia transacción.
    """
    if conexion is not None:
        db = Session(
            bind=conexion,
            join_transaction_mode="create_savepoint",
            expire_on_commit=False,
        )
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
        return

    with engine.connect() as conn:
        transaccion = conn.begin()
        db = Session(
            bind=conn,
            join_transaction_mode="create_savepoint",
            expire_on_commit=False,
        )
        try:
            yield db
            db.commit()
            transaccion.commit()
        except Exception:
            db.rollback()
            transaccion.rollback()
            raise
        finally:
            db.close()


def _leer_parametros(engine: Engine) -> tuple[date, Decimal]:
    """Fecha de corte y peso máximo, antes de escribir cualquier cosa."""
    with Session(bind=engine) as db:
        crudo = str(parametros.get_param(db, CLAVE_FECHA_CORTE)).strip()
        if not crudo:
            raise ParametroNoDefinido(CLAVE_FECHA_CORTE)
        try:
            fecha_corte = date.fromisoformat(crudo)
        except ValueError as exc:
            raise ErrorParametroMigracion(
                f"{CLAVE_FECHA_CORTE} debe ser una fecha ISO (aaaa-mm-dd): {crudo!r}"
            ) from exc
        peso_max = parametros.get_param(db, CLAVE_PESO_MAX_KG)
    return fecha_corte, Decimal(str(peso_max))


def _fila_vacia(fila: FilaCruda) -> bool:
    return all(not valor.strip() for valor in fila.valores.values())


def _texto_original(fila: FilaCruda) -> str:
    """Hoja, fila y valores crudos de las celdas, sin normalizar."""
    return json.dumps(
        {"hoja": HOJA, "fila": fila.numero, "valores": fila.valores},
        ensure_ascii=False,
        sort_keys=True,
    )


def _hash_fila(fila: FilaCruda) -> str:
    return hashlib.sha256(_texto_original(fila).encode("utf-8")).hexdigest()


def cargar_padron(
    *,
    ruta_excel: Path,
    salida: Path,
    engine: Engine,
    simular: bool = False,
) -> ReporteCarga:
    """Carga la hoja de clientes y mascotas y escribe reporte y revisión."""
    fecha_corte, peso_max = _leer_parametros(engine)
    libro = leer_libro(ruta_excel)
    hoja = libro.hojas[HOJA]
    reporte = ReporteCarga(simulacion=simular)
    en_revision: list[FilaRevision] = []

    def procesar(conexion: Connection | None) -> None:
        for fila in hoja.filas:
            if _fila_vacia(fila):
                continue
            reporte.leidas += 1
            _procesar_con_transaccion(
                engine, conexion, fila, fecha_corte, peso_max, reporte, en_revision
            )

    if simular:
        with engine.connect() as conn:
            transaccion = conn.begin()
            try:
                procesar(conn)
            finally:
                transaccion.rollback()
    else:
        procesar(None)

    escribir_revision(en_revision, ruta_revision(salida, simular=simular))
    escribir_reporte(reporte, salida)
    return reporte


def _procesar_con_transaccion(
    engine: Engine,
    conexion: Connection | None,
    fila: FilaCruda,
    fecha_corte: date,
    peso_max: Decimal,
    reporte: ReporteCarga,
    en_revision: list[FilaRevision],
) -> None:
    hash_fila = _hash_fila(fila)
    texto_original = _texto_original(fila)
    resultado: _ResultadoFila | None = None

    try:
        with _sesion_fila(engine, conexion) as db:
            registro = repository.obtener(db, HOJA, fila.numero)
            if registro is not None and registro.estado == ESTADO_CARGADA:
                if registro.hash_fila == hash_fila:
                    reporte.ya_cargadas += 1
                else:
                    reporte.cambiadas += 1
                return
            resultado = _procesar_fila(db, fila, fecha_corte, peso_max)
            _guardar_registro(db, registro, fila, hash_fila, texto_original, resultado)
    except Exception as exc:  # una fila rota no corta la migración
        _registrar_error(
            engine, conexion, fila, hash_fila, texto_original, exc, reporte
        )
        return

    if resultado is None:
        return

    if resultado.estado == ESTADO_CARGADA:
        reporte.cargadas += 1
        if resultado.mascota_existente:
            reporte.mascotas_existentes += 1
        if resultado.conflicto is not None:
            reporte.conflictos_peso.append(resultado.conflicto)
        return

    motivo = resultado.motivo or "sin_motivo"
    reporte.a_revision[motivo] += 1
    en_revision.append(
        FilaRevision(
            hoja=HOJA,
            fila=fila.numero,
            id_origen=fila.valores["ID_Registro"].strip(),
            campo=resultado.campo,
            valor_original=resultado.valor_original,
            motivo=motivo,
            accion_sugerida=resultado.accion,
        )
    )


def _registrar_error(
    engine: Engine,
    conexion: Connection | None,
    fila: FilaCruda,
    hash_fila: str,
    texto_original: str,
    error: Exception,
    reporte: ReporteCarga,
) -> None:
    reporte.errores += 1
    motivo = f"error_inesperado: {type(error).__name__}"
    try:
        with _sesion_fila(engine, conexion) as db:
            registro = repository.obtener(db, HOJA, fila.numero)
            _guardar_registro(
                db,
                registro,
                fila,
                hash_fila,
                texto_original,
                _ResultadoFila(estado=ESTADO_ERROR, motivo=motivo),
            )
    except Exception:  # el reporte ya cuenta el error de la fila
        return


def _guardar_registro(
    db: Session,
    registro: MigracionRegistro | None,
    fila: FilaCruda,
    hash_fila: str,
    texto_original: str,
    resultado: _ResultadoFila,
) -> None:
    datos: dict[str, Any] = {
        "id_origen": fila.valores["ID_Registro"].strip() or None,
        "hash_fila": hash_fila,
        "texto_original": texto_original,
        "entidad": resultado.entidad,
        "entidad_id": resultado.entidad_id,
        "estado": resultado.estado,
        "motivo": resultado.motivo,
        "origen_confirmacion": None,
    }
    if registro is None:
        repository.crear(
            db, MigracionRegistro(hoja=HOJA, fila=fila.numero, **datos)
        )
    else:
        repository.actualizar(db, registro, datos)


def _revision(campo: str, valor: str, motivo: str, accion: str) -> _ResultadoFila:
    return _ResultadoFila(
        estado=ESTADO_REVISION,
        motivo=motivo,
        campo=campo,
        valor_original=valor,
        accion=accion,
    )


def _procesar_fila(
    db: Session,
    fila: FilaCruda,
    fecha_corte: date,
    peso_max: Decimal,
) -> _ResultadoFila:
    valores = fila.valores
    nombre, apellido, _ = limpiar_nombre_dueno(valores["Nombre_Duenio"])
    if not nombre:
        return _revision(
            "Nombre_Duenio", valores["Nombre_Duenio"], "nombre_vacio", "COMPLETAR_NOMBRE"
        )
    if not apellido:
        return _revision(
            "Nombre_Duenio",
            valores["Nombre_Duenio"],
            "persona_sin_apellido",
            "COMPLETAR_APELLIDO",
        )

    edad_texto = valores["Edad_Aprox"]
    meses = edad_a_meses(edad_texto)
    if meses is None and edad_texto.strip():
        return _revision(
            "Edad_Aprox", edad_texto, "edad_no_reconocida", "COMPLETAR_EDAD"
        )
    nacimiento = fecha_nacimiento_aprox(fecha_corte, meses) if meses is not None else None

    especie, raza, tamanio = especie_raza(valores["Especie_Raza"])
    if especie is None:
        return _revision(
            "Especie_Raza", valores["Especie_Raza"], "especie_no_deducible", "COMPLETAR_ESPECIE"
        )

    telefono_texto = valores["Telefono_Contacto"]
    numero = telefono(
        telefono_texto, lambda texto: padron_service.normalizar_telefono(db, texto)
    )
    if numero == REVISION:
        return _revision(
            "Telefono_Contacto",
            telefono_texto,
            "telefono_no_reconocido",
            "CORREGIR_TELEFONO",
        )

    peso_texto = valores["Peso_Kg"]
    peso = peso_kg(peso_texto)
    if peso is None and peso_texto.strip():
        return _revision("Peso_Kg", peso_texto, "peso_no_reconocido", "CORREGIR_PESO")
    if peso is not None and peso > peso_max:
        return _revision("Peso_Kg", peso_texto, "peso_fuera_de_rango", "CORREGIR_PESO")

    nombre_mascota = " ".join(valores["Nombre_Mascota"].split())
    if not nombre_mascota:
        return _revision(
            "Nombre_Mascota", valores["Nombre_Mascota"], "mascota_sin_nombre", "COMPLETAR_MASCOTA"
        )

    especie_id = _especie_id(db, especie)
    if especie_id is None:
        return _revision(
            "Especie_Raza", valores["Especie_Raza"], "especie_no_configurada", "CONFIGURAR_ESPECIE"
        )

    persona = _resolver_persona(db, nombre, apellido, numero, telefono_texto)
    if isinstance(persona, _ResultadoFila):
        return persona

    if persona is None:
        creada = _crear_persona(db, nombre, apellido, numero, telefono_texto, valores)
        if isinstance(creada, _ResultadoFila):
            return creada
        persona_id = creada
    else:
        persona_id = persona

    raza_id = _raza_id(db, especie_id, raza)
    tamanio_id = _tamanio_id(db, tamanio)

    try:
        return _resolver_mascota(
            db,
            fila,
            persona_id,
            nombre_mascota,
            especie_id,
            raza_id,
            tamanio_id,
            peso,
            nacimiento,
        )
    except DatosInvalidos:
        return _revision(
            "Nombre_Mascota",
            valores["Nombre_Mascota"],
            "datos_invalidos",
            "REVISAR_DATO",
        )


def _resolver_persona(
    db: Session,
    nombre: str,
    apellido: str,
    numero: str,
    telefono_texto: str,
) -> int | _ResultadoFila | None:
    """Persona existente según teléfono + nombre; ``None`` si hay que crearla."""
    claves = claves_de_comparacion(nombre, apellido)

    if numero != SIN_TELEFONO:
        candidatos = padron_service.buscar_personas(
            db, telefono=numero, limite=LIMITE_BUSQUEDA
        )
        for candidato in candidatos:
            if claves_de_comparacion(candidato.nombre, candidato.apellido) == claves:
                return candidato.id
        if candidatos:
            return _revision(
                "Telefono_Contacto",
                telefono_texto,
                "telefono_de_otra_persona",
                f"ASOCIAR_A:{candidatos[0].id}",
            )
        return None

    candidatos = padron_service.buscar_personas(
        db, texto=apellido, limite=LIMITE_BUSQUEDA
    )
    for candidato in candidatos:
        if claves_de_comparacion(candidato.nombre, candidato.apellido) != claves:
            continue
        if candidato.telefonos:
            return _revision(
                "Telefono_Contacto",
                telefono_texto,
                "nombre_con_otro_telefono",
                f"ASOCIAR_A:{candidato.id}",
            )
        return _revision(
            "Telefono_Contacto",
            telefono_texto,
            "persona_sin_telefono_duplicada",
            f"ASOCIAR_A:{candidato.id}",
        )
    return None


def _crear_persona(
    db: Session,
    nombre: str,
    apellido: str,
    numero: str,
    telefono_texto: str,
    valores: dict[str, str],
) -> int | _ResultadoFila:
    referencia = " ".join(valores["Direccion_Localidad"].split())
    datos = padron_schemas.PersonaNueva(
        nombre=nombre,
        apellido=apellido,
        dni=None,
        domicilio=(
            padron_schemas.DomicilioNuevo(referencia=referencia) if referencia else None
        ),
        telefonos=[telefono_texto] if numero != SIN_TELEFONO else [],
    )
    try:
        persona = padron_service.crear_persona(
            db, datos, migrado=True, creado_por=None
        )
    except PosibleDuplicado as exc:
        candidato = exc.coincidencias[0].persona.id if exc.coincidencias else 0
        return _revision(
            "Nombre_Duenio",
            valores["Nombre_Duenio"],
            "posible_duplicado",
            f"ASOCIAR_A:{candidato}" if candidato else "REVISAR_DUPLICADO",
        )
    except DniDuplicado:
        return _revision(
            "Nombre_Duenio", valores["Nombre_Duenio"], "dni_duplicado", "REVISAR_DUPLICADO"
        )
    except DatosInvalidos:
        return _revision(
            "Nombre_Duenio", valores["Nombre_Duenio"], "datos_invalidos", "REVISAR_DATO"
        )
    return persona.id


def _resolver_mascota(
    db: Session,
    fila: FilaCruda,
    persona_id: int,
    nombre: str,
    especie_id: int,
    raza_id: int | None,
    tamanio_id: int | None,
    peso: Decimal | None,
    nacimiento: date | None,
) -> _ResultadoFila:
    clave = clave_comparable(nombre)
    for resumen in padron_service.pacientes_de_persona(db, persona_id):
        if clave_comparable(resumen.nombre) != clave:
            continue
        detalle = padron_service.obtener_paciente(db, resumen.id)
        if detalle is None:
            continue
        conflicto = None
        if peso is not None and detalle.peso_kg is not None and detalle.peso_kg != peso:
            anterior = repository.obtener_por_entidad(db, ENTIDAD_PACIENTE, detalle.id)
            padron_service.actualizar_paciente(
                db, detalle.id, padron_schemas.PacienteActualizar(peso_kg=peso)
            )
            conflicto = ConflictoPeso(
                paciente_id=detalle.id,
                fila_anterior=anterior.fila if anterior is not None else 0,
                fila_nueva=fila.numero,
                peso_anterior=str(detalle.peso_kg),
                peso_nuevo=str(peso),
            )
        return _ResultadoFila(
            estado=ESTADO_CARGADA,
            entidad=ENTIDAD_PACIENTE,
            entidad_id=detalle.id,
            mascota_existente=True,
            conflicto=conflicto,
        )

    paciente = padron_service.crear_paciente(
        db,
        padron_schemas.PacienteNuevo(
            nombre=nombre,
            especie_id=especie_id,
            raza_id=raza_id,
            tamanio_id=tamanio_id,
            peso_kg=peso,
            fecha_nacimiento_aprox=nacimiento,
            titular_persona_id=persona_id,
        ),
        titular_persona_id=persona_id,
    )
    return _ResultadoFila(
        estado=ESTADO_CARGADA, entidad=ENTIDAD_PACIENTE, entidad_id=paciente.id
    )


def _especie_id(db: Session, nombre: str) -> int | None:
    clave = normalizacion.clave_comparable(nombre)
    for especie in padron_service.listar_especies(db):
        if normalizacion.clave_comparable(especie.nombre) == clave:
            return especie.id
    return None


def _raza_id(db: Session, especie_id: int, nombre: str | None) -> int | None:
    if not nombre:
        return None
    clave = normalizacion.clave_comparable(nombre)
    for raza in padron_service.listar_razas(db, especie_id=especie_id):
        if normalizacion.clave_comparable(raza.nombre) == clave:
            return raza.id
    creada = padron_service.crear_raza(
        db, padron_schemas.RazaNueva(nombre=nombre, especie_id=especie_id)
    )
    return creada.id


def _tamanio_id(db: Session, nombre: str | None) -> int | None:
    if not nombre:
        return None
    clave = normalizacion.clave_comparable(nombre)
    for tamanio in padron_service.listar_tamanios(db):
        if normalizacion.clave_comparable(tamanio.nombre) == clave:
            return tamanio.id
    return None
