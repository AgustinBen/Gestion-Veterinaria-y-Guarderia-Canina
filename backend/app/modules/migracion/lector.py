from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet


class ErrorLecturaExcel(Exception):
    """Error de lectura del Excel."""


class HojaFaltanteError(ErrorLecturaExcel):
    def __init__(self, hoja: str, hojas_disponibles: list[str]) -> None:
        super().__init__(f"Falta la hoja obligatoria '{hoja}'. Hojas disponibles: {hojas_disponibles}")
        self.hoja = hoja
        self.hojas_disponibles = hojas_disponibles


class ColumnaFaltanteError(ErrorLecturaExcel):
    def __init__(self, hoja: str, columna: str, columnas_disponibles: list[str]) -> None:
        super().__init__(
            f"Falta la columna obligatoria '{columna}' en la hoja '{hoja}'. "
            f"Columnas disponibles: {columnas_disponibles}"
        )
        self.hoja = hoja
        self.columna = columna
        self.columnas_disponibles = columnas_disponibles


HOJAS_OBLIGATORIAS = ["Clientes_y_Mascotas", "Atenciones_Clinicas", "Guarderia_y_Estadias"]

COLUMNAS_OBLIGATORIAS: dict[str, list[str]] = {
    "Clientes_y_Mascotas": [
        "ID_Registro",
        "Nombre_Duenio",
        "Telefono_Contacto",
        "Nombre_Mascota",
        "Especie_Raza",
        "Edad_Aprox",
        "Peso_Kg",
        "Direccion_Localidad",
    ],
    "Atenciones_Clinicas": [
        "Nro_Ficha",
        "Fecha_Visita",
        "Paciente_Mascota",
        "Duenio_Referencia",
        "Tipo_Servicio",
        "Detalle_Clinico_y_Cobro",
        "Veterinario_Tratante",
    ],
    "Guarderia_y_Estadias": [
        "Nro_Reserva",
        "Mascota",
        "Tutor",
        "Fecha_Ingreso",
        "Fecha_Egreso",
        "Modalidad",
        "Tarifa_Total",
        "Estado_Pago",
        "Comportamiento_Cuidados",
    ],
}


def obtener_ruta_excel(excel_origen: str | None = None) -> Path:
    if excel_origen is None:
        excel_origen = os.environ.get("EXCEL_ORIGEN", "")
    ruta = Path(excel_origen) if excel_origen else Path("data")
    if ruta.is_dir():
        # Buscar archivo .xlsx en data/
        candidatos = sorted(ruta.glob("*.xlsx"))
        if not candidatos:
            raise ErrorLecturaExcel(f"No se encontró archivo .xlsx en {ruta}")
        return candidatos[0]
    return ruta


def _celda_a_texto(valor: Any) -> tuple[str, bool, bool]:
    """Convierte celda a texto. Retorna (texto, es_fecha_nativa, es_vacia)."""
    if valor is None:
        return "", False, True
    if isinstance(valor, datetime):
        # Fecha nativa de Excel - mantener como categoría aparte
        return valor.isoformat(), True, False
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        # Leer todo como texto, pero preservar representación
        # Para evitar notación científica, convertir a str
        s = str(valor)
        return s, False, s.strip() == ""
    if isinstance(valor, bool):
        s = "true" if valor else "false"
        return s, False, False
    s = str(valor)
    # Si viene como texto con fecha tipo "2026-05-11 00:00:00", lo dejamos como texto para clasificarlo
    return s, False, s.strip() == ""


def leer_excel(ruta_excel: str | Path) -> dict[str, Any]:
    ruta = Path(ruta_excel)
    wb = load_workbook(filename=str(ruta), read_only=True, data_only=True)
    try:
        hojas_disponibles = wb.sheetnames
        for hoja_req in HOJAS_OBLIGATORIAS:
            if hoja_req not in hojas_disponibles:
                raise HojaFaltanteError(hoja_req, hojas_disponibles)

        resultado_hojas: dict[str, Any] = {}
        for nombre_hoja in HOJAS_OBLIGATORIAS:
            ws: Worksheet = wb[nombre_hoja]
            filas = list(ws.iter_rows(values_only=True))
            if not filas:
                raise ErrorLecturaExcel(f"La hoja '{nombre_hoja}' está vacía o no tiene encabezados")
            encabezados = []
            for h in filas[0]:
                if h is None:
                    encabezados.append("")
                else:
                    encabezados.append(str(h).strip())
            # Validar columnas obligatorias
            columnas_obligatorias = COLUMNAS_OBLIGATORIAS[nombre_hoja]
            for col_req in columnas_obligatorias:
                if col_req not in encabezados:
                    raise ColumnaFaltanteError(nombre_hoja, col_req, encabezados)
            # Mapear índices
            idx_map = {col: i for i, col in enumerate(encabezados)}
            datos_filas = []
            for fila_num, fila_vals in enumerate(filas[1:], start=2):  # start at 2 (excel row)
                fila_dict: dict[str, Any] = {}
                tiene_algo = False
                for col in columnas_obligatorias:
                    val = fila_vals[idx_map[col]] if idx_map[col] < len(fila_vals) else None
                    texto, es_fecha_nativa, es_vacia = _celda_a_texto(val)
                    fila_dict[col] = {
                        "texto": texto,
                        "es_fecha_nativa": es_fecha_nativa,
                        "es_vacia": es_vacia,
                        "valor_original": val,
                    }
                    if not es_vacia:
                        tiene_algo = True
                datos_filas.append({
                    "fila_excel": fila_num,
                    "valores": fila_dict,
                    "totalmente_vacia": not tiene_algo,
                })
            resultado_hojas[nombre_hoja] = {
                "encabezados": encabezados,
                "filas": datos_filas,
                "cantidad_filas": len(datos_filas),
            }

        fecha_ultima_edicion = None
        advertencia_fecha = None
        if wb.properties.modified is not None:
            fecha_ultima_edicion = wb.properties.modified.isoformat()
        else:
            fecha_ultima_edicion = None
            advertencia_fecha = "No hay fecha de última edición en las propiedades del libro (workbook.properties.modified es None)"

        return {
            "hojas": resultado_hojas,
            "fecha_ultima_edicion": fecha_ultima_edicion,
            "advertencia_fecha": advertencia_fecha,
            "ruta": str(ruta),
        }
    finally:
        wb.close()
