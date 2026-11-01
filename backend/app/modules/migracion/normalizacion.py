"""Normalización de la hoja Clientes_y_Mascotas (T-16, RN-05, RN-08 y RN-50).

Funciones puras: no acceden a la base de datos. El teléfono se delega en la
función oficial de ``padron``, que el consumidor inyecta ya ligada a su sesión
(``padron.service.normalizar_telefono``) para no duplicar la regla. Las fechas y
el peso se delegan en el perfilado de T-15. Nada se corrige en silencio: lo que
no se reconoce se informa para que la carga lo mande a revisión.
"""

from __future__ import annotations

import calendar
import re
from collections.abc import Callable
from datetime import date
from decimal import Decimal

from app.modules.migracion import perfilado
from app.modules.padron.service import DatosInvalidos

SIN_TELEFONO = "SIN_TELEFONO"
REVISION = "REVISION"

NormalizadorTelefono = Callable[[str], str]

MESES_POR_ANIO = 12
MESES_POR_MEDIO_ANIO = 6

# Títulos que el Excel antepone al nombre del dueño (se descartan del nombre).
TITULOS: dict[str, str] = {
    "dr": "Dr.",
    "dra": "Dra.",
}

# Textos del Excel que significan "esta persona no tiene teléfono". La clave es
# el texto normalizado; el valor, la etiqueta para el reporte. Es editable.
CENTINELAS_SIN_TELEFONO: dict[str, str] = {
    "sin telefono": "sin teléfono",
    "no tiene telefono": "no tiene teléfono",
    "no hay telefono": "no hay teléfono",
    "sin numero": "sin número",
    "sin celular": "sin celular",
}

# Diccionarios editables de especie, raza y tamaño. Sin especie explícita no se
# asume nada: el registro va a revisión (RN-05).
ESPECIES: dict[str, str] = {
    "perro": "Perro",
    "perros": "Perro",
    "canino": "Perro",
    "canina": "Perro",
    "caninos": "Perro",
    "caninas": "Perro",
    "gato": "Gato",
    "gatos": "Gato",
    "gata": "Gato",
    "gatas": "Gato",
    "felino": "Gato",
    "felina": "Gato",
    "felinos": "Gato",
    "felinas": "Gato",
}

TAMANIOS: dict[str, str] = {
    "chico": "Chico",
    "chica": "Chico",
    "pequenio": "Chico",  # "pequeño" normalizado
    "pequenia": "Chico",
    "mediano": "Mediano",
    "mediana": "Mediano",
    "grande": "Grande",
}

RAZAS: dict[str, str] = {
    "labrador": "Labrador",
    "siames": "Siames",
    "siamesa": "Siames",
    "caniche": "Caniche",
    "mestizo": "Mestizo",
    "mestiza": "Mestizo",
    "criollo": "Criollo",
    "criolla": "Criollo",
}

# Razas conocidas que implican su especie (decisión del equipo). La clave es el
# nombre que se guarda, con tildes; la búsqueda se hace sobre el texto
# normalizado y gana el nombre más largo. "Mestizo" no está: no implica especie
# y se resuelve con RAZAS cuando el texto ya dice la especie.
RAZAS_CON_ESPECIE: dict[str, str] = {
    "Ovejero Alemán": "Perro",
    "Caniche": "Perro",
    "Bulldog Francés": "Perro",
    "Labrador": "Perro",
    "Golden Retriever": "Perro",
    "Beagle": "Perro",
    "Pastor": "Perro",
    "Siamés": "Gato",
    "Persa": "Gato",
}

# (texto normalizado, nombre para guardar, especie) de más largo a más corto:
# si se agrega una raza que contiene a otra, la más específica gana.
_RAZAS_POR_LONGITUD: tuple[tuple[str, str, str], ...] = tuple(
    sorted(
        (
            (perfilado.normalizar_texto(nombre), nombre, especie)
            for nombre, especie in RAZAS_CON_ESPECIE.items()
        ),
        key=lambda item: len(item[0]),
        reverse=True,
    )
)

_CONECTORES = frozenset({"de", "del", "y", "raza"})

_PATRON_TITULO = re.compile(r"^(dr|dra)\.?\s+", re.IGNORECASE)
_PATRON_EDAD_MEDIO = re.compile(r"^(\d+)\s*años?\s*y\s*medio\s*$", re.IGNORECASE)
_PATRON_EDAD_ANIOS = re.compile(r"^(\d+)\s*años?\s*(?:aprox\.?)?\s*$", re.IGNORECASE)
_PATRON_EDAD_MESES = re.compile(r"^(\d+)\s*mes(?:es)?\s*$", re.IGNORECASE)
_PATRON_EDAD_SOLA = re.compile(r"^(\d+)\s*$")
_PATRON_PARENTESIS = re.compile(r"\([^)]*\)")
_SEPARADORES = re.compile(r"[\s,/\-]+")


def _formatear(texto: str) -> str:
    """Texto para guardar: espacios simples y cada palabra capitalizada."""
    return " ".join(parte.capitalize() for parte in texto.split())


def limpiar_nombre_dueno(
    texto: str,
) -> tuple[str | None, str | None, str | None]:
    """Separa nombre, apellido y título del dueño.

    El último término es el apellido (RN-08). Un solo término devuelve
    ``apellido=None`` para que la carga lo mande a revisión: nunca se inventa
    un apellido.
    """
    limpio = " ".join((texto or "").split())
    titulo: str | None = None
    coincidencia = _PATRON_TITULO.match(limpio)
    if coincidencia:
        titulo = TITULOS[coincidencia.group(1).casefold()]
        limpio = limpio[coincidencia.end() :].strip()
    if not limpio:
        return None, None, titulo

    partes = limpio.split(" ")
    if len(partes) == 1:
        return _formatear(partes[0]), None, titulo
    return _formatear(" ".join(partes[:-1])), _formatear(partes[-1]), titulo


def edad_a_meses(texto: str) -> int | None:
    """Edad del Excel en meses; ``None`` si el texto no se reconoce.

    "3 años" y "4" se leen en años; "8 meses" y "2 años y medio" en meses. La
    edad nunca se guarda: se convierte en fecha de nacimiento (RN-09).
    """
    limpio = (texto or "").strip()
    if not limpio:
        return None

    coincidencia = _PATRON_EDAD_MEDIO.match(limpio)
    if coincidencia:
        return int(coincidencia.group(1)) * MESES_POR_ANIO + MESES_POR_MEDIO_ANIO

    for patron in (_PATRON_EDAD_ANIOS, _PATRON_EDAD_SOLA):
        coincidencia = patron.match(limpio)
        if coincidencia:
            return int(coincidencia.group(1)) * MESES_POR_ANIO

    coincidencia = _PATRON_EDAD_MESES.match(limpio)
    if coincidencia:
        return int(coincidencia.group(1))
    return None


def fecha_nacimiento_aprox(fecha_corte: date, meses: int) -> date:
    """Fecha de nacimiento aproximada: fecha de corte menos la edad en meses.

    Se conserva el día del corte y se ajusta al último día del mes cuando no
    existe (por ejemplo, 31 de enero menos un mes).
    """
    if meses < 0:
        raise ValueError("La edad en meses no puede ser negativa")

    total = fecha_corte.year * MESES_POR_ANIO + (fecha_corte.month - 1) - meses
    anio, mes = divmod(total, MESES_POR_ANIO)
    ultimo_dia = calendar.monthrange(anio, mes + 1)[1]
    return date(anio, mes + 1, min(fecha_corte.day, ultimo_dia))


def fecha(texto: str) -> date | None:
    """Fecha ISO delegada en el clasificador de T-15; ``None`` si no sirve."""
    return perfilado.clasificar_fecha(texto).fecha


def peso_kg(texto: str) -> Decimal | None:
    """Peso en ``Decimal`` delegado en el parser de T-15 ("12,5 kg" → 12.5)."""
    parseado = perfilado.convertir_peso_kg(texto.strip())
    return parseado.valor if parseado is not None else None


def _razas_detectadas(clave: str) -> list[tuple[str, str]]:
    """Razas del mapa presentes en el texto, de la más larga a la más corta."""
    detectadas: list[tuple[str, str]] = []
    resto = clave
    for texto, nombre, especie in _RAZAS_POR_LONGITUD:
        if texto in resto:
            detectadas.append((nombre, especie))
            resto = resto.replace(texto, " ")
    return detectadas


def especie_raza(texto: str) -> tuple[str | None, str | None, str | None]:
    """Especie, raza y tamaño según los diccionarios editables.

    Una raza conocida implica su especie (``RAZAS_CON_ESPECIE``); si el texto ya
    dice la especie, esa tiene prioridad. Dos razas de especies distintas, o
    ninguna raza ni especie reconocible, devuelven ``especie=None``: la carga
    manda la fila a revisión y nunca asume perro ni gato (RN-05).
    """
    clave = perfilado.normalizar_texto(texto or "")
    if not clave:
        return None, None, None

    especie: str | None = None
    tamanio: str | None = None
    resto: list[str] = []
    for token in _SEPARADORES.split(clave):
        if not token or token in _CONECTORES:
            continue
        if especie is None and token in ESPECIES:
            especie = ESPECIES[token]
        elif tamanio is None and token in TAMANIOS:
            tamanio = TAMANIOS[token]
        else:
            resto.append(RAZAS.get(token, token))

    detectadas = _razas_detectadas(clave)
    if len({especie_detectada for _, especie_detectada in detectadas}) > 1:
        return None, None, None
    if detectadas:
        nombre_raza, especie_de_raza = detectadas[0]
        return (especie or especie_de_raza), nombre_raza, tamanio

    raza = _formatear(" ".join(resto)) if resto else None
    return especie, raza, tamanio


def _es_centinela_sin_telefono(clave: str) -> bool:
    sin_parentesis = " ".join(_PATRON_PARENTESIS.sub(" ", clave).split())
    return (
        clave in CENTINELAS_SIN_TELEFONO
        or sin_parentesis in CENTINELAS_SIN_TELEFONO
    )


def telefono(texto: str, normalizar: NormalizadorTelefono) -> str:
    """Teléfono normalizado, ``SIN_TELEFONO`` o ``REVISION``.

    ``normalizar`` es la función oficial de padrón ligada a su sesión. Se usa la
    lista de textos centinela para las personas que declararon no tener
    teléfono; cualquier otro texto que no resuelva va a revisión.
    """
    clave = perfilado.normalizar_texto(texto or "")
    if not clave or _es_centinela_sin_telefono(clave):
        return SIN_TELEFONO
    try:
        return normalizar(texto.strip())
    except (DatosInvalidos, ValueError):
        return REVISION


def clave_comparable(texto: str | None) -> str:
    """Forma de comparación: sin tildes ni mayúsculas. No se guarda."""
    return perfilado.normalizar_texto(texto or "")


def claves_de_comparacion(
    nombre: str | None, apellido: str | None
) -> tuple[str, str]:
    """Claves para decidir si dos filas son la misma persona; nunca se fusionan."""
    return clave_comparable(nombre), clave_comparable(apellido)
