"""Almacenamiento seguro de archivos adjuntos de estudios clínicos."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

TAMANO_BLOQUE = 64 * 1024
_NOMBRE_GENERADO = re.compile(r"[0-9a-f]{32}\Z")


class ArchivoDemasiadoGrande(Exception):
    """El archivo excede el límite configurado."""


class TipoArchivoNoPermitido(Exception):
    """El contenido no coincide con un tipo habilitado."""


@dataclass(frozen=True)
class ArchivoAlmacenado:
    nombre_archivo: str
    tipo_mime: str
    tamano_bytes: int
    sha256: str
    ruta: Path


def _tipo_por_firma(contenido: bytes) -> str | None:
    if contenido.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if contenido.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(contenido) >= 12 and contenido.startswith(b"RIFF") and contenido[8:12] == b"WEBP":
        return "image/webp"
    if contenido.startswith(b"%PDF-"):
        return "application/pdf"
    return None


def guardar(
    origen: BinaryIO,
    directorio: Path,
    *,
    max_bytes: int,
    tipos_permitidos: set[str],
) -> ArchivoAlmacenado:
    primer_bloque = origen.read(TAMANO_BLOQUE)
    if not primer_bloque:
        raise TipoArchivoNoPermitido("El archivo está vacío o no tiene una firma válida")
    if len(primer_bloque) > max_bytes:
        raise ArchivoDemasiadoGrande()

    tipo_mime = _tipo_por_firma(primer_bloque)
    if tipo_mime is None or tipo_mime not in tipos_permitidos:
        raise TipoArchivoNoPermitido("El tipo de archivo no está permitido")

    directorio = directorio.resolve()
    directorio.mkdir(parents=True, exist_ok=True)
    nombre_archivo = uuid4().hex
    ruta = directorio / nombre_archivo
    digest = hashlib.sha256()
    tamano = 0
    creado = False

    try:
        with ruta.open("xb") as destino:
            creado = True
            bloque = primer_bloque
            while bloque:
                tamano += len(bloque)
                if tamano > max_bytes:
                    raise ArchivoDemasiadoGrande()
                destino.write(bloque)
                digest.update(bloque)
                bloque = origen.read(TAMANO_BLOQUE)
    except Exception:
        if creado:
            ruta.unlink(missing_ok=True)
        raise

    return ArchivoAlmacenado(
        nombre_archivo=nombre_archivo,
        tipo_mime=tipo_mime,
        tamano_bytes=tamano,
        sha256=digest.hexdigest(),
        ruta=ruta,
    )


def ruta_archivo(directorio: Path, nombre_archivo: str) -> Path:
    if _NOMBRE_GENERADO.fullmatch(nombre_archivo) is None:
        raise ValueError("Nombre de archivo almacenado inválido")
    return directorio.resolve() / nombre_archivo


def eliminar(ruta: Path) -> None:
    ruta.unlink(missing_ok=True)
