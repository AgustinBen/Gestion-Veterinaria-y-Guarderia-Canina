"""Perfilado de calidad del Excel histórico de migración (T-15).

El módulo es de solo lectura: no usa base de datos, no importa otros módulos y
no modifica el Excel. Construye conteos y hallazgos para que T-16 decida qué
limpiar.
"""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Callable, cast

from app.modules.migracion.lector import FilaCruda, HojaCruda, LibroCrudo, leer_libro

NOMBRE_CLIENTES = "Clientes_y_Mascotas"
NOMBRE_ATENCIONES = "Atenciones_Clinicas"
NOMBRE_GUARDERIA = "Guarderia_y_Estadias"

FORMATOS_FECHA = ("dd/mm/aaaa", "aaaa-mm-dd", "d de Mes aaaa", "dd/mm/aa")

MESES: dict[str, int] = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

PREFIJOS_TELEFONO = ("54", "9", "0", "15")
PALABRAS_DEUDA = ("deuda", "debe", "deben", "fiado", "adeuda", "pendiente")

MOTIVO_FILA_VACIA = "fila_vacia"
MOTIVO_TELEFONO_VACIO = "telefono_vacio"
MOTIVO_TELEFONO_LETRAS = "telefono_con_letras"
MOTIVO_TELEFONO_VARIOS = "telefono_con_varios_numeros"
MOTIVO_FECHA_INVALIDA = "fecha_invalida"
MOTIVO_FECHA_NO_RECONOCIDA = "fecha_no_reconocida"
MOTIVO_EDAD_NO_RECONOCIDA = "edad_no_reconocida"
MOTIVO_PESO_NO_RECONOCIDO = "peso_no_reconocido"
MOTIVO_SIN_APELLIDO = "persona_sin_apellido"
MOTIVO_DUPLICADO_TELEFONO = "duplicado_telefono"
MOTIVO_DUPLICADO_DUENIO = "duplicado_duenio"
MOTIVO_DUPLICADO_MASCOTA = "duplicado_mascota"
MOTIVO_MASCOTA_SIN_DUENIO = "mascota_sin_duenio"
MOTIVO_DEUDA = "deuda_en_texto"

_PATRON_DDMMAAAA = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")
_PATRON_AAAAMMDD = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_PATRON_DDMMAA = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{2})$")
_PATRON_TEXTO = re.compile(r"^(\d{1,2}) de ([A-Za-zÁÉÍÓÚÜáéíóúü]+) (?:de )?(\d{4})$")
_PATRON_EDAD_ANIOS = re.compile(r"^\s*(\d+)\s*años?\s*(?:aprox\.?)?\s*$", re.IGNORECASE)
_PATRON_EDAD_MEDIO = re.compile(r"^\s*(\d+)\s*años?\s*y\s*medio\s*$", re.IGNORECASE)
_PATRON_EDAD_MESES = re.compile(r"^\s*(\d+)\s*mes(?:es)?\s*$", re.IGNORECASE)
_PATRON_EDAD_SOLA = re.compile(r"^\s*(\d+)\s*$")
_PATRON_PESO = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*(kg)?\s*$", re.IGNORECASE)
_PATRON_TITULO = re.compile(r"^(dr|dra)\.?\s+", re.IGNORECASE)
_PATRON_DEUDA = re.compile(
    r"\b(" + "|".join(PALABRAS_DEUDA) + r")\b",
    re.IGNORECASE,
)

COLUMNAS_DEUDA: dict[str, tuple[str, ...]] = {
    NOMBRE_ATENCIONES: ("Detalle_Clinico_y_Cobro",),
    NOMBRE_GUARDERIA: ("Estado_Pago",),
}

COLUMNAS_FECHA: dict[str, tuple[str, ...]] = {
    NOMBRE_ATENCIONES: ("Fecha_Visita",),
    NOMBRE_GUARDERIA: ("Fecha_Ingreso", "Fecha_Egreso"),
}


class ErrorSinDatos(Exception):
    """El libro no tiene ninguna fila con datos."""


@dataclass(frozen=True)
class Hallazgo:
    hoja: str
    fila: int
    columna: str
    motivo: str
    valor_original: str


@dataclass(frozen=True)
class ReportePerfilado:
    datos: dict[str, object]
    hallazgos: tuple[Hallazgo, ...]


@dataclass(frozen=True)
class ClasificacionFecha:
    fecha: date | None
    formato: str | None
    motivo: str | None


@dataclass(frozen=True)
class PesoParseado:
    valor: Decimal
    con_unidad: bool
    separador: str | None


def normalizar_texto(valor: str) -> str:
    """Texto comparable: sin tildes, sin mayúsculas y con espacios simples."""
    sin_tildes = "".join(
        caracter
        for caracter in unicodedata.normalize("NFKD", valor)
        if not unicodedata.combining(caracter)
    )
    return " ".join(sin_tildes.casefold().split())


def _solo_digitos(valor: str) -> str:
    return re.sub(r"\D", "", valor)


def _cantidad_numeros(valor: str) -> int:
    compacto = re.sub(r"[\s().-]", "", valor)
    return len(re.findall(r"\d{6,}", compacto))


def normalizar_telefono_temporal(valor: str | None) -> str:
    """Normalización temporal de T-15.

    temporal: se reconcilia con la normalización oficial de padron en T-16.
    Solo saca 54 y 9 cuando el número tiene más de 10 dígitos; 0 y 15 se sacan
    como prefijo siempre.
    """
    digitos = _solo_digitos(valor or "")
    if len(digitos) > 10:
        for prefijo in ("54", "9"):
            if digitos.startswith(prefijo):
                digitos = digitos[len(prefijo) :]
    if digitos.startswith("0"):
        digitos = digitos[1:]
    if digitos.startswith("15"):
        digitos = digitos[2:]
    return digitos


def es_agrupable_telefono(valor: str) -> bool:
    """Indica si el teléfono puede usarse para agrupar duplicados."""
    texto = valor.strip()
    if not texto:
        return False
    if any(caracter.isalpha() for caracter in texto):
        return False
    if _cantidad_numeros(texto) != 1:
        return False
    return bool(_solo_digitos(texto))


def forma_telefono(valor: str) -> str:
    """Máscara estable para contar formatos sin exponer el número."""
    return re.sub(r"\d", "#", valor.strip())


def _fecha(dia: int, mes: int, anio: int, formato: str) -> ClasificacionFecha:
    try:
        return ClasificacionFecha(fecha=date(anio, mes, dia), formato=formato, motivo=None)
    except ValueError:
        return ClasificacionFecha(fecha=None, formato=formato, motivo=MOTIVO_FECHA_INVALIDA)


def clasificar_fecha(valor: str) -> ClasificacionFecha:
    """Clasifica una fecha en uno de los cuatro formatos reales del Excel."""
    texto = valor.strip()
    if not texto:
        return ClasificacionFecha(fecha=None, formato=None, motivo=None)

    coincidencia = _PATRON_DDMMAAAA.match(texto)
    if coincidencia:
        dia, mes, anio = (int(parte) for parte in coincidencia.groups())
        return _fecha(dia, mes, anio, "dd/mm/aaaa")

    coincidencia = _PATRON_AAAAMMDD.match(texto)
    if coincidencia:
        anio, mes, dia = (int(parte) for parte in coincidencia.groups())
        return _fecha(dia, mes, anio, "aaaa-mm-dd")

    coincidencia = _PATRON_TEXTO.match(texto)
    if coincidencia:
        dia_texto, nombre_mes, anio_texto = coincidencia.groups()
        mes_texto = MESES.get(normalizar_texto(nombre_mes))
        if mes_texto is not None:
            return _fecha(int(dia_texto), mes_texto, int(anio_texto), "d de Mes aaaa")

    coincidencia = _PATRON_DDMMAA.match(texto)
    if coincidencia:
        dia, mes, anio_corto = (int(parte) for parte in coincidencia.groups())
        return _fecha(dia, mes, 2000 + anio_corto, "dd/mm/aa")

    return ClasificacionFecha(fecha=None, formato=None, motivo=MOTIVO_FECHA_NO_RECONOCIDA)


def convertir_edad_anios(valor: str) -> int | None:
    """Convierte las edades del Excel a años enteros; None = no reconocida."""
    texto = valor.strip()
    if not texto:
        return None

    if _PATRON_EDAD_MESES.match(texto):
        return 0

    for patron in (_PATRON_EDAD_MEDIO, _PATRON_EDAD_ANIOS, _PATRON_EDAD_SOLA):
        coincidencia = patron.match(texto)
        if coincidencia:
            return int(coincidencia.group(1))
    return None


def convertir_peso_kg(valor: str) -> PesoParseado | None:
    """Convierte el peso a Decimal, aceptando kg opcional y coma o punto."""
    coincidencia = _PATRON_PESO.match(valor)
    if not coincidencia:
        return None

    numero, unidad = coincidencia.groups()
    separador: str | None = None
    if "," in numero:
        separador = ","
    elif "." in numero:
        separador = "."

    try:
        peso = Decimal(numero.replace(",", "."))
    except InvalidOperation:
        return None

    return PesoParseado(valor=peso, con_unidad=unidad is not None, separador=separador)


def menciona_deuda(valor: str) -> bool:
    return _PATRON_DEUDA.search(normalizar_texto(valor)) is not None


def _fila_vacia(fila: FilaCruda) -> bool:
    return all(not valor.strip() for valor in fila.valores.values())


def _filas_con_datos(hoja: HojaCruda) -> list[FilaCruda]:
    return [fila for fila in hoja.filas if not _fila_vacia(fila)]


def _limpiar_titulo(nombre: str) -> str:
    limpio = " ".join(nombre.split())
    return " ".join(_PATRON_TITULO.sub("", limpio).split())


def _es_sin_apellido(nombre: str) -> bool:
    limpio = _limpiar_titulo(nombre)
    if not limpio:
        return False
    return len(limpio.split()) == 1


def _agregar_grupo(
    grupos: dict[str, list[FilaCruda]],
    clave: str,
    fila: FilaCruda,
) -> None:
    if clave:
        grupos.setdefault(clave, []).append(fila)


def _grupos_duplicados(grupos: dict[str, list[FilaCruda]]) -> list[list[FilaCruda]]:
    repetidos = [filas for filas in grupos.values() if len(filas) >= 2]
    return sorted(repetidos, key=lambda filas: tuple(fila.numero for fila in filas))


def _detalle_grupos(grupos: list[list[FilaCruda]], hoja: str) -> list[dict[str, object]]:
    detalle: list[dict[str, object]] = []
    for grupo in grupos:
        detalle.append(
            {
                "filas": [
                    {"hoja": hoja, "fila": fila.numero}
                    for fila in sorted(grupo, key=lambda fila: fila.numero)
                ]
            }
        )
    return detalle


def _hallazgos_duplicados(
    grupos: list[list[FilaCruda]],
    hoja: str,
    columna: str,
    motivo: str,
    valor_de: Callable[[FilaCruda], str],
) -> list[Hallazgo]:
    hallazgos: list[Hallazgo] = []
    for grupo in grupos:
        for fila in grupo:
            hallazgos.append(
                Hallazgo(
                    hoja=hoja,
                    fila=fila.numero,
                    columna=columna,
                    motivo=motivo,
                    valor_original=valor_de(fila),
                )
            )
    return hallazgos


def _mapa(datos: dict[str, object], clave: str) -> dict[str, object]:
    valor = datos.get(clave)
    if isinstance(valor, dict):
        return cast(dict[str, object], valor)
    return {}


def _entero(mapa: dict[str, object], clave: str) -> int:
    valor = mapa.get(clave)
    return valor if isinstance(valor, int) else 0


def construir_perfilado(libro: LibroCrudo) -> ReportePerfilado:
    """Construye todos los conteos y hallazgos del libro."""
    cliente = libro.hojas[NOMBRE_CLIENTES]
    atenciones = libro.hojas[NOMBRE_ATENCIONES]
    guarderia = libro.hojas[NOMBRE_GUARDERIA]

    conteo_filas_por_hoja: dict[str, object] = {}
    total_con_datos = 0
    for nombre, hoja in libro.hojas.items():
        con_datos = len(_filas_con_datos(hoja))
        total_con_datos += con_datos
        conteo_filas_por_hoja[nombre] = {
            "filas_totales": len(hoja.filas) + 1,
            "filas_hoja": len(hoja.filas),
            "filas_con_datos": con_datos,
        }

    if total_con_datos == 0:
        raise ErrorSinDatos("El libro no tiene ninguna fila con datos.")

    hallazgos: list[Hallazgo] = []
    filas_clientes = _filas_con_datos(cliente)
    filas_atenciones = _filas_con_datos(atenciones)
    filas_guarderia = _filas_con_datos(guarderia)

    # Filas totalmente vacías.
    filas_vacias_detalle: list[dict[str, object]] = []
    for nombre, hoja in libro.hojas.items():
        for fila in hoja.filas:
            if _fila_vacia(fila):
                filas_vacias_detalle.append({"hoja": nombre, "fila": fila.numero})
                hallazgos.append(
                    Hallazgo(
                        hoja=nombre,
                        fila=fila.numero,
                        columna="",
                        motivo=MOTIVO_FILA_VACIA,
                        valor_original="",
                    )
                )

    # Teléfonos.
    telefonos_vacios = 0
    telefonos_con_letras = 0
    telefonos_con_varios = 0
    telefonos_sin_digitos = 0
    telefonos_con_digitos = 0
    telefonos_agrupables = 0
    formas: Counter[str] = Counter()
    grupos_telefono: dict[str, list[FilaCruda]] = {}
    for fila in filas_clientes:
        original = fila.valores["Telefono_Contacto"]
        texto = original.strip()
        if not texto:
            telefonos_vacios += 1
            hallazgos.append(
                Hallazgo(
                    hoja=NOMBRE_CLIENTES,
                    fila=fila.numero,
                    columna="Telefono_Contacto",
                    motivo=MOTIVO_TELEFONO_VACIO,
                    valor_original=original,
                )
            )
            continue

        formas[forma_telefono(texto)] += 1
        if any(caracter.isalpha() for caracter in texto):
            telefonos_con_letras += 1
            hallazgos.append(
                Hallazgo(
                    hoja=NOMBRE_CLIENTES,
                    fila=fila.numero,
                    columna="Telefono_Contacto",
                    motivo=MOTIVO_TELEFONO_LETRAS,
                    valor_original=original,
                )
            )
        if _cantidad_numeros(texto) > 1:
            telefonos_con_varios += 1
            hallazgos.append(
                Hallazgo(
                    hoja=NOMBRE_CLIENTES,
                    fila=fila.numero,
                    columna="Telefono_Contacto",
                    motivo=MOTIVO_TELEFONO_VARIOS,
                    valor_original=original,
                )
            )
        if _solo_digitos(texto):
            telefonos_con_digitos += 1
        else:
            telefonos_sin_digitos += 1
        if es_agrupable_telefono(texto):
            telefonos_agrupables += 1
            _agregar_grupo(
                grupos_telefono,
                normalizar_telefono_temporal(texto),
                fila,
            )

    grupos_telefono_validos = _grupos_duplicados(grupos_telefono)
    hallazgos.extend(
        _hallazgos_duplicados(
            grupos_telefono_validos,
            NOMBRE_CLIENTES,
            "Telefono_Contacto",
            MOTIVO_DUPLICADO_TELEFONO,
            lambda fila: fila.valores["Telefono_Contacto"],
        )
    )

    telefonos = {
        "total_celdas": len(filas_clientes),
        "vacias": telefonos_vacios,
        "con_letras": telefonos_con_letras,
        "con_varios_numeros": telefonos_con_varios,
        "formatos_distintos": len(formas),
        "agrupables": telefonos_agrupables,
        "con_digitos": telefonos_con_digitos,
        "sin_digitos": telefonos_sin_digitos,
        "variantes": [
            {"formato": formato, "cantidad": cantidad}
            for formato, cantidad in sorted(formas.items())
        ],
    }

    # Duplicados de dueño y mascota (solo hoja de clientes).
    grupos_duenio: dict[str, list[FilaCruda]] = {}
    grupos_mascota: dict[str, list[FilaCruda]] = {}
    for fila in filas_clientes:
        _agregar_grupo(
            grupos_duenio,
            normalizar_texto(fila.valores["Nombre_Duenio"]),
            fila,
        )
        duenio = normalizar_texto(fila.valores["Nombre_Duenio"])
        mascota = normalizar_texto(fila.valores["Nombre_Mascota"])
        if duenio and mascota:
            _agregar_grupo(grupos_mascota, f"{duenio}|{mascota}", fila)

    duenios_duplicados = _grupos_duplicados(grupos_duenio)
    mascotas_duplicadas = _grupos_duplicados(grupos_mascota)
    hallazgos.extend(
        _hallazgos_duplicados(
            duenios_duplicados,
            NOMBRE_CLIENTES,
            "Nombre_Duenio",
            MOTIVO_DUPLICADO_DUENIO,
            lambda fila: fila.valores["Nombre_Duenio"],
        )
    )
    hallazgos.extend(
        _hallazgos_duplicados(
            mascotas_duplicadas,
            NOMBRE_CLIENTES,
            "Nombre_Mascota",
            MOTIVO_DUPLICADO_MASCOTA,
            lambda fila: fila.valores["Nombre_Mascota"],
        )
    )

    # Mascotas sin dueño: par (dueño normalizado, mascota normalizada).
    pares_clientes = {
        (
            normalizar_texto(fila.valores["Nombre_Duenio"]),
            normalizar_texto(fila.valores["Nombre_Mascota"]),
        )
        for fila in filas_clientes
        if fila.valores["Nombre_Duenio"].strip() and fila.valores["Nombre_Mascota"].strip()
    }
    mascotas_sin_duenio: set[tuple[str, str]] = set()
    mascotas_sin_duenio_detalle: list[dict[str, object]] = []
    for nombre_hoja, filas, columna_duenio, columna_mascota in (
        (NOMBRE_ATENCIONES, filas_atenciones, "Duenio_Referencia", "Paciente_Mascota"),
        (NOMBRE_GUARDERIA, filas_guarderia, "Tutor", "Mascota"),
    ):
        for fila in filas:
            duenio = normalizar_texto(fila.valores[columna_duenio])
            mascota = normalizar_texto(fila.valores[columna_mascota])
            if not duenio or not mascota:
                continue
            if (duenio, mascota) in pares_clientes:
                continue
            mascotas_sin_duenio.add((duenio, mascota))
            mascotas_sin_duenio_detalle.append({"hoja": nombre_hoja, "fila": fila.numero})
            hallazgos.append(
                Hallazgo(
                    hoja=nombre_hoja,
                    fila=fila.numero,
                    columna=columna_mascota,
                    motivo=MOTIVO_MASCOTA_SIN_DUENIO,
                    valor_original=fila.valores[columna_mascota],
                )
            )

    # Personas sin apellido: dueños, tutores y veterinarios.
    # Las referencias de dueño/tutor que ya existen en clientes no se vuelven a
    # listar: la persona se perfila una sola vez, en su fila de origen.
    duenios_sin_apellido: set[str] = set()
    veterinarios_sin_apellido: set[str] = set()
    filas_sin_apellido = 0
    nombres_de_clientes = {
        normalizar_texto(fila.valores["Nombre_Duenio"])
        for fila in filas_clientes
        if fila.valores["Nombre_Duenio"].strip()
    }

    def registrar_sin_apellido(
        nombre_hoja: str,
        fila: FilaCruda,
        columna: str,
        destino: set[str],
        *,
        omitir_repetido: bool,
    ) -> None:
        nonlocal filas_sin_apellido
        nombre = fila.valores[columna]
        if omitir_repetido and normalizar_texto(nombre) in nombres_de_clientes:
            return
        if not _es_sin_apellido(nombre):
            return
        destino.add(normalizar_texto(_limpiar_titulo(nombre)))
        filas_sin_apellido += 1
        hallazgos.append(
            Hallazgo(
                hoja=nombre_hoja,
                fila=fila.numero,
                columna=columna,
                motivo=MOTIVO_SIN_APELLIDO,
                valor_original=nombre,
            )
        )

    for fila in filas_clientes:
        registrar_sin_apellido(
            NOMBRE_CLIENTES,
            fila,
            "Nombre_Duenio",
            duenios_sin_apellido,
            omitir_repetido=False,
        )
    for fila in filas_atenciones:
        registrar_sin_apellido(
            NOMBRE_ATENCIONES,
            fila,
            "Duenio_Referencia",
            duenios_sin_apellido,
            omitir_repetido=True,
        )
        registrar_sin_apellido(
            NOMBRE_ATENCIONES,
            fila,
            "Veterinario_Tratante",
            veterinarios_sin_apellido,
            omitir_repetido=False,
        )
    for fila in filas_guarderia:
        registrar_sin_apellido(
            NOMBRE_GUARDERIA,
            fila,
            "Tutor",
            duenios_sin_apellido,
            omitir_repetido=True,
        )

    # Fechas.
    por_formato_total: dict[str, int] = {formato: 0 for formato in FORMATOS_FECHA}
    fechas_por_columna: dict[str, object] = {}
    fechas_invalidas = 0
    fechas_no_reconocidas = 0
    fechas_vacias = 0
    fechas_total = 0
    for nombre_hoja, columnas in COLUMNAS_FECHA.items():
        filas = filas_atenciones if nombre_hoja == NOMBRE_ATENCIONES else filas_guarderia
        for columna in columnas:
            por_formato: dict[str, int] = {formato: 0 for formato in FORMATOS_FECHA}
            invalidas = 0
            no_reconocidas = 0
            vacias = 0
            total_columna = 0
            for fila in filas:
                original = fila.valores[columna]
                texto = original.strip()
                total_columna += 1
                fechas_total += 1
                if not texto:
                    vacias += 1
                    fechas_vacias += 1
                    continue
                clasificacion = clasificar_fecha(texto)
                if clasificacion.fecha is not None and clasificacion.formato is not None:
                    por_formato[clasificacion.formato] += 1
                    por_formato_total[clasificacion.formato] += 1
                elif clasificacion.motivo == MOTIVO_FECHA_INVALIDA:
                    invalidas += 1
                    fechas_invalidas += 1
                    hallazgos.append(
                        Hallazgo(
                            hoja=nombre_hoja,
                            fila=fila.numero,
                            columna=columna,
                            motivo=MOTIVO_FECHA_INVALIDA,
                            valor_original=original,
                        )
                    )
                else:
                    no_reconocidas += 1
                    fechas_no_reconocidas += 1
                    hallazgos.append(
                        Hallazgo(
                            hoja=nombre_hoja,
                            fila=fila.numero,
                            columna=columna,
                            motivo=MOTIVO_FECHA_NO_RECONOCIDA,
                            valor_original=original,
                        )
                    )

            fechas_por_columna[f"{nombre_hoja}.{columna}"] = {
                "total_celdas": total_columna,
                "vacias": vacias,
                "por_formato": por_formato,
                "invalidas": invalidas,
                "no_reconocidas": no_reconocidas,
            }

    fechas = {
        "total_celdas": fechas_total,
        "vacias": fechas_vacias,
        "por_formato": por_formato_total,
        "invalidas": fechas_invalidas,
        "no_reconocidas": fechas_no_reconocidas,
        "por_columna": fechas_por_columna,
    }

    # Edad.
    edad_vacias = 0
    edad_reconocidas = 0
    edad_no_reconocidas = 0
    edad_por_anio: Counter[str] = Counter()
    for fila in filas_clientes:
        original = fila.valores["Edad_Aprox"]
        texto = original.strip()
        if not texto:
            edad_vacias += 1
            continue
        anios = convertir_edad_anios(texto)
        if anios is None:
            edad_no_reconocidas += 1
            hallazgos.append(
                Hallazgo(
                    hoja=NOMBRE_CLIENTES,
                    fila=fila.numero,
                    columna="Edad_Aprox",
                    motivo=MOTIVO_EDAD_NO_RECONOCIDA,
                    valor_original=original,
                )
            )
            continue
        edad_reconocidas += 1
        edad_por_anio[str(anios)] += 1

    edad = {
        "total_celdas": len(filas_clientes),
        "vacias": edad_vacias,
        "reconocidas": edad_reconocidas,
        "no_reconocidas": edad_no_reconocidas,
        "por_anio": dict(sorted(edad_por_anio.items())),
    }

    # Peso.
    peso_vacias = 0
    peso_con_unidad = 0
    peso_sin_unidad = 0
    peso_separador_coma = 0
    peso_separador_punto = 0
    peso_validos = 0
    peso_no_reconocidos = 0
    for fila in filas_clientes:
        original = fila.valores["Peso_Kg"]
        texto = original.strip()
        if not texto:
            peso_vacias += 1
            continue
        parseado = convertir_peso_kg(texto)
        if parseado is None:
            peso_no_reconocidos += 1
            hallazgos.append(
                Hallazgo(
                    hoja=NOMBRE_CLIENTES,
                    fila=fila.numero,
                    columna="Peso_Kg",
                    motivo=MOTIVO_PESO_NO_RECONOCIDO,
                    valor_original=original,
                )
            )
            continue
        peso_validos += 1
        if parseado.con_unidad:
            peso_con_unidad += 1
        else:
            peso_sin_unidad += 1
        if parseado.separador == ",":
            peso_separador_coma += 1
        elif parseado.separador == ".":
            peso_separador_punto += 1

    peso = {
        "total_celdas": len(filas_clientes),
        "vacias": peso_vacias,
        "con_unidad": peso_con_unidad,
        "sin_unidad": peso_sin_unidad,
        "separador_coma": peso_separador_coma,
        "separador_punto": peso_separador_punto,
        "validos": peso_validos,
        "no_reconocidos": peso_no_reconocidos,
    }

    # Especie y raza.
    especie_vacias = 0
    valores_especie: list[str] = []
    originales_por_normalizado: dict[str, set[str]] = {}
    filas_por_normalizado: Counter[str] = Counter()
    for fila in filas_clientes:
        original = fila.valores["Especie_Raza"]
        texto = original.strip()
        if not texto:
            especie_vacias += 1
            continue
        valores_especie.append(texto)
        normalizado = normalizar_texto(texto)
        originales_por_normalizado.setdefault(normalizado, set()).add(texto)
        filas_por_normalizado[normalizado] += 1

    variantes_especie: list[dict[str, object]] = []
    for normalizado, originales in sorted(originales_por_normalizado.items()):
        if len(originales) < 2:
            continue
        variantes_especie.append(
            {
                "normalizado": normalizado,
                "originales": sorted(originales),
                "cantidad": filas_por_normalizado[normalizado],
            }
        )

    especie_raza = {
        "total_celdas": len(filas_clientes),
        "vacias": especie_vacias,
        "valores_distintos": len(set(valores_especie)),
        "normalizados_distintos": len(originales_por_normalizado),
        "grupos_variantes": len(variantes_especie),
        "variantes": variantes_especie,
    }

    # Deuda mencionada en el texto.
    deuda_detalle: list[dict[str, object]] = []
    for nombre_hoja, columnas in COLUMNAS_DEUDA.items():
        filas = filas_atenciones if nombre_hoja == NOMBRE_ATENCIONES else filas_guarderia
        for fila in filas:
            for columna in columnas:
                original = fila.valores[columna]
                if menciona_deuda(original):
                    deuda_detalle.append({"hoja": nombre_hoja, "fila": fila.numero})
                    hallazgos.append(
                        Hallazgo(
                            hoja=nombre_hoja,
                            fila=fila.numero,
                            columna=columna,
                            motivo=MOTIVO_DEUDA,
                            valor_original=original,
                        )
                    )
                    break

    # DNI: el Excel de origen no lo tiene; se informa una sola vez.
    columna_dni_presente = any(
        "dni" in encabezado.casefold()
        for hoja in libro.hojas.values()
        for encabezado in hoja.encabezados
    )
    dni: dict[str, object] = {"columna_presente": columna_dni_presente}
    if not columna_dni_presente:
        dni["hallazgo"] = (
            "El Excel no tiene columna DNI; los clientes migrados se completan después (RN-02)."
        )

    fecha_ultima_edicion = libro.fecha_ultima_edicion
    datos: dict[str, object] = {
        "conteo_filas_por_hoja": conteo_filas_por_hoja,
        "fecha_ultima_edicion": (
            fecha_ultima_edicion.isoformat() if fecha_ultima_edicion is not None else None
        ),
        "fecha_corte_propuesta": (
            fecha_ultima_edicion.date().isoformat() if fecha_ultima_edicion is not None else None
        ),
        "advertencia_fecha": (
            "Fecha de corte propuesta a validar con el cliente (pendiente 8)."
            if fecha_ultima_edicion is not None
            else "El libro no informa fecha de última edición; no se propone fecha de corte."
        ),
        "telefonos": telefonos,
        "fechas": fechas,
        "edad": edad,
        "peso": peso,
        "especie_raza": especie_raza,
        "dni": dni,
        "sin_apellido": {
            "personas_unicas": len(duenios_sin_apellido | veterinarios_sin_apellido),
            "duenios_tutores_unicos": len(duenios_sin_apellido),
            "veterinarios_unicos": len(veterinarios_sin_apellido),
            "filas": filas_sin_apellido,
        },
        "duplicados": {
            "por_telefono": {
                "grupos": len(grupos_telefono_validos),
                "filas": sum(len(grupo) for grupo in grupos_telefono_validos),
                "detalle": _detalle_grupos(grupos_telefono_validos, NOMBRE_CLIENTES),
            },
            "por_duenio": {
                "grupos": len(duenios_duplicados),
                "filas": sum(len(grupo) for grupo in duenios_duplicados),
                "detalle": _detalle_grupos(duenios_duplicados, NOMBRE_CLIENTES),
            },
            "por_mascota": {
                "grupos": len(mascotas_duplicadas),
                "filas": sum(len(grupo) for grupo in mascotas_duplicadas),
                "detalle": _detalle_grupos(mascotas_duplicadas, NOMBRE_CLIENTES),
            },
        },
        "mascotas_sin_duenio": {
            "pares_unicos": len(mascotas_sin_duenio),
            "filas": len(mascotas_sin_duenio_detalle),
            "detalle": mascotas_sin_duenio_detalle,
        },
        "filas_totalmente_vacias": {
            "cantidad": len(filas_vacias_detalle),
            "detalle": filas_vacias_detalle,
        },
        "deuda_en_el_texto": {
            "filas": len(deuda_detalle),
            "detalle": deuda_detalle,
        },
    }

    return ReportePerfilado(datos=datos, hallazgos=tuple(hallazgos))


def _orden_hallazgo(hallazgo: Hallazgo) -> tuple[str, int, str, str, str]:
    return (
        hallazgo.hoja,
        hallazgo.fila,
        hallazgo.columna,
        hallazgo.motivo,
        hallazgo.valor_original,
    )


def escribir_salidas(reporte: ReportePerfilado, directorio: Path) -> None:
    """Escribe perfilado.json y perfilado_filas.csv de forma determinista."""
    directorio.mkdir(parents=True, exist_ok=True)

    json_destino = directorio / "perfilado.json"
    json_destino.write_text(
        json.dumps(reporte.datos, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    csv_destino = directorio / "perfilado_filas.csv"
    with csv_destino.open("w", encoding="utf-8-sig", newline="") as archivo:
        escritor = csv.writer(archivo, lineterminator="\n")
        escritor.writerow(["hoja", "fila", "columna", "motivo", "valor_original"])
        for hallazgo in sorted(reporte.hallazgos, key=_orden_hallazgo):
            escritor.writerow(
                [
                    hallazgo.hoja,
                    hallazgo.fila,
                    hallazgo.columna,
                    hallazgo.motivo,
                    hallazgo.valor_original,
                ]
            )


def perfilar(ruta_excel: Path, directorio_salida: Path) -> ReportePerfilado:
    """Lee, perfila y escribe las salidas."""
    libro = leer_libro(ruta_excel)
    reporte = construir_perfilado(libro)
    escribir_salidas(reporte, directorio_salida)
    return reporte


def resumen_consola(reporte: ReportePerfilado) -> str:
    """Resumen sin datos personales para mostrar por consola."""
    datos = reporte.datos
    filas = _mapa(datos, "conteo_filas_por_hoja")
    fechas = _mapa(datos, "fechas")
    telefonos = _mapa(datos, "telefonos")
    edad = _mapa(datos, "edad")
    peso = _mapa(datos, "peso")
    especie = _mapa(datos, "especie_raza")

    lineas = [
        "Perfilado completado.",
        "Filas con datos: "
        + ", ".join(
            f"{nombre}={_entero(_mapa(filas, nombre), 'filas_con_datos')}"
            for nombre in filas
        ),
        "Fechas: "
        f"total={_entero(fechas, 'total_celdas')}, "
        f"invalidas={_entero(fechas, 'invalidas')}, "
        f"no_reconocidas={_entero(fechas, 'no_reconocidas')}",
        "Telefonos: "
        f"total={_entero(telefonos, 'total_celdas')}, "
        f"vacios={_entero(telefonos, 'vacias')}, "
        f"con_letras={_entero(telefonos, 'con_letras')}, "
        f"con_varios={_entero(telefonos, 'con_varios_numeros')}, "
        f"formatos={_entero(telefonos, 'formatos_distintos')}, "
        f"agrupables={_entero(telefonos, 'agrupables')}",
        "Edad: "
        f"total={_entero(edad, 'total_celdas')}, "
        f"reconocidas={_entero(edad, 'reconocidas')}, "
        f"no_reconocidas={_entero(edad, 'no_reconocidas')}",
        "Peso: "
        f"total={_entero(peso, 'total_celdas')}, "
        f"validos={_entero(peso, 'validos')}, "
        f"no_reconocidos={_entero(peso, 'no_reconocidos')}",
        "Especie/raza: "
        f"total={_entero(especie, 'total_celdas')}, "
        f"distintos={_entero(especie, 'valores_distintos')}, "
        f"normalizados={_entero(especie, 'normalizados_distintos')}",
        f"Hallazgos: {len(reporte.hallazgos)}",
    ]
    return "\n".join(lineas)
