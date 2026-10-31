"""Fixtures del módulo de migración: Excel ficticio con defectos conocidos."""

from __future__ import annotations

from pathlib import Path

import pytest
from openpyxl import Workbook

COLUMNAS_CLIENTES = (
    "ID_Registro",
    "Nombre_Duenio",
    "Telefono_Contacto",
    "Nombre_Mascota",
    "Especie_Raza",
    "Edad_Aprox",
    "Peso_Kg",
    "Direccion_Localidad",
)

COLUMNAS_ATENCIONES = (
    "Nro_Ficha",
    "Fecha_Visita",
    "Paciente_Mascota",
    "Duenio_Referencia",
    "Tipo_Servicio",
    "Detalle_Clinico_y_Cobro",
    "Veterinario_Tratante",
)

COLUMNAS_GUARDERIA = (
    "Nro_Reserva",
    "Mascota",
    "Tutor",
    "Fecha_Ingreso",
    "Fecha_Egreso",
    "Modalidad",
    "Tarifa_Total",
    "Estado_Pago",
    "Comportamiento_Cuidados",
)

FILAS_CLIENTES = (
    (
        "REG-001",
        "VALERIA GOMEZ",
        "+54 9 11 4455-8899",
        "Firulais",
        "Perro - Labrador",
        "4 años",
        "28,5 kg",
        "Av. Siempre Viva 742, CABA",
    ),
    (
        "REG-002",
        "valeria gomez",
        "11 4455-8899",
        "Firulais",
        "perro - labrador",
        "4",
        "28.5kg",
        "Av. Siempre Viva 742, CABA",
    ),
    (
        "REG-003",
        "MARCOS PEREZ",
        "15-6677-2233",
        "Chicho",
        "Gato - Siames",
        "3 años aprox",
        "4 kg",
        "San Martin 100, CABA",
    ),
    (
        "REG-004",
        "Lucia",
        "Sin telefono (dejo mail)",
        "Titan",
        "canino",
        "6 meses",
        "",
        "Rivadavia 200, CABA",
    ),
    (
        "REG-005",
        "ANA LOPEZ",
        "",
        "Rocco Jr.",
        "Mestizo mediano",
        "2 años y medio",
        "12,25",
        "Belgrano 300, CABA",
    ),
    (
        "REG-006",
        "ANA LOPEZ",
        "011 4890-1122",
        "Rocco",
        "Mestizo mediano",
        "no sé",
        "12 kg",
        "Belgrano 300, CABA",
    ),
    (
        "REG-007",
        "PEDRO",
        "11 5555-1234 / 11 6666-5678",
        "Luna",
        "Gato Siames",
        "10",
        "3.5",
        "Mitre 400, Rosario",
    ),
    (
        "REG-008",
        "CARLA DIAZ",
        "341-555-0000",
        "Nala",
        "Perro - Caniche",
        "8 años",
        "6,4 kg",
        "Cordoba 500, Rosario",
    ),
    ("", "", "", "", "", "", "", ""),
)

FILAS_ATENCIONES = (
    (
        "A-001",
        "12/03/2024",
        "Firulais",
        "VALERIA GOMEZ",
        "Consulta",
        "Control sano",
        "Dr. Juan Perez",
    ),
    (
        "A-002",
        "2024-05-04",
        "Chicho",
        "MARCOS PEREZ",
        "Vacunación",
        "Antirrábica",
        "Dra. Laura",
    ),
    (
        "A-003",
        "7 de junio 2024",
        "Firulais",
        "VALERIA GOMEZ",
        "Consulta",
        "Control",
        "Dr. Juan Perez",
    ),
    (
        "A-004",
        "05/06/24",
        "Titan",
        "Lucia",
        "Cirugía",
        "Castración",
        "Dra. Laura",
    ),
    (
        "A-005",
        "ayer",
        "Firulais",
        "JULIA SOSA",
        "Consulta",
        "Debe $5000",
        "Dra. Laura",
    ),
    (
        "A-006",
        "31/02/2024",
        "Luna",
        "PEDRO",
        "Consulta",
        "Control",
        "Dr. Juan Perez",
    ),
)

FILAS_GUARDERIA = (
    (
        "G-001",
        "Rocco Jr.",
        "ANA LOPEZ",
        "2024-07-01",
        "03/07/2024",
        "Día",
        "15000",
        "Pagado",
        "Tranquilo",
    ),
    (
        "G-002",
        "Rocco",
        "ANA LOPEZ",
        "15/07/24",
        "17/07/24",
        "Noche",
        "15000",
        "Debe $3000",
        "Juguetón",
    ),
    (
        "G-003",
        "Chicho",
        "MARCOS PEREZ",
        "2024-08-01",
        "2024-08-03",
        "Día",
        "12000",
        "Fiado",
        "Tranquilo",
    ),
    (
        "G-004",
        "Titan",
        "Lucia",
        "01/09/2024",
        "02/09/2024",
        "Noche",
        "12000",
        "Pagado",
        "",
    ),
    (
        "G-005",
        "Firulais",
        "JULIA SOSA",
        "10 de octubre de 2024",
        "12 de octubre de 2024",
        "Día",
        "10000",
        "Pagado",
        "Tranquilo",
    ),
)


def _agregar_hoja(libro: Workbook, nombre: str, columnas: tuple[str, ...], filas: tuple[tuple[str, ...], ...]) -> None:
    hoja = libro.create_sheet(title=nombre)
    hoja.append(columnas)
    for fila in filas:
        hoja.append(fila)


def _crear_excel(ruta: Path) -> None:
    libro = Workbook()
    libro.remove(libro.active)
    _agregar_hoja(libro, "Clientes_y_Mascotas", COLUMNAS_CLIENTES, FILAS_CLIENTES)
    _agregar_hoja(libro, "Atenciones_Clinicas", COLUMNAS_ATENCIONES, FILAS_ATENCIONES)
    _agregar_hoja(libro, "Guarderia_y_Estadias", COLUMNAS_GUARDERIA, FILAS_GUARDERIA)
    libro.save(ruta)
    libro.close()


@pytest.fixture
def excel_ficticio(tmp_path: Path) -> Path:
    ruta = tmp_path / "excel_ficticio.xlsx"
    _crear_excel(ruta)
    return ruta
