"""Archivo de revisión manual de la migración (T-16).

Escribe ``revision.csv`` (o ``revision_simulada.csv`` en simulación) con las
filas que necesitan una decisión humana. Nunca pisa una decisión ya cargada:
la columna ``decision`` se conserva por (hoja, fila).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

COLUMNAS = (
    "hoja",
    "fila",
    "id_origen",
    "campo",
    "valor_original",
    "motivo",
    "accion_sugerida",
    "decision",
)

NOMBRE_REVISION = "revision.csv"
NOMBRE_REVISION_SIMULADA = "revision_simulada.csv"


@dataclass(frozen=True)
class FilaRevision:
    hoja: str
    fila: int
    id_origen: str
    campo: str
    valor_original: str
    motivo: str
    accion_sugerida: str
    decision: str = ""


def ruta_revision(directorio: Path, *, simular: bool) -> Path:
    nombre = NOMBRE_REVISION_SIMULADA if simular else NOMBRE_REVISION
    return directorio / nombre


def _decisiones_previas(ruta: Path) -> dict[tuple[str, int], str]:
    if not ruta.is_file():
        return {}

    decisiones: dict[tuple[str, int], str] = {}
    with ruta.open(encoding="utf-8-sig", newline="") as archivo:
        for registro in csv.DictReader(archivo):
            decision = (registro.get("decision") or "").strip()
            if not decision:
                continue
            try:
                fila = int(registro.get("fila") or "")
            except ValueError:
                continue
            decisiones[(registro.get("hoja") or "", fila)] = decision
    return decisiones


def escribir_revision(filas: Iterable[FilaRevision], ruta: Path) -> None:
    """Escribe el CSV completo conservando las decisiones humanas previas."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    decisiones = _decisiones_previas(ruta)

    with ruta.open("w", encoding="utf-8-sig", newline="") as archivo:
        escritor = csv.writer(archivo, lineterminator="\n")
        escritor.writerow(COLUMNAS)
        for fila in sorted(filas, key=lambda item: (item.hoja, item.fila, item.campo)):
            decision = fila.decision or decisiones.get((fila.hoja, fila.fila), "")
            escritor.writerow(
                [
                    fila.hoja,
                    fila.fila,
                    fila.id_origen,
                    fila.campo,
                    fila.valor_original,
                    fila.motivo,
                    fila.accion_sugerida,
                    decision,
                ]
            )
