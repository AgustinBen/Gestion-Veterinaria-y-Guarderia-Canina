from __future__ import annotations

from pathlib import Path

import pytest
from openpyxl import Workbook


@pytest.fixture
def excel_ficticio_t15(tmp_path: Path) -> Path:
    """Crea un Excel ficticio con los defectos requeridos para T-15."""
    wb = Workbook()

    # Eliminar hoja por defecto
    default = wb.active
    wb.remove(default)

    # Clientes_y_Mascotas
    ws_clientes = wb.create_sheet("Clientes_y_Mascotas")
    headers_clientes = [
        "ID_Registro",
        "Nombre_Duenio",
        "Telefono_Contacto",
        "Nombre_Mascota",
        "Especie_Raza",
        "Edad_Aprox",
        "Peso_Kg",
        "Direccion_Localidad",
    ]
    ws_clientes.append(headers_clientes)
    # REG-001: Juan Perez, 11 4455-8899, Firulais
    ws_clientes.append(["REG-001", "Juan Perez", "11 4455-8899", "Firulais", "Perro - Labrador", "4 años", "28,5", "Calle Falsa 123"])
    # REG-002: Juan Perez, 1144558899 (mismo teléfono otro formato), Firulais - misma_persona
    ws_clientes.append(["REG-002", "Juan Perez", "1144558899", "Firulais", "Perro - Labrador", "4", "29", "Calle Falsa 123"])
    # REG-003: Maria Lopez, Chicho (en padrón)
    ws_clientes.append(["REG-003", "Maria Lopez", "15-6677-2233", "Chicho", "Perro - Mestizo", "2 años y medio", "12", "Av. Siempreviva 45"])
    # REG-004: Carlos Gomez, 011 6677-2233, Titan (en padrón) - mismo teléfono que luego familia
    ws_clientes.append(["REG-004", "Carlos Gomez", "011 6677-2233", "Titan", "Gato - Siames", "6 meses", "4", "Belgrano 10"])
    # REG-005: Ana Torres sin teléfono, Rocco Jr (en padrón)
    ws_clientes.append(["REG-005", "Ana Torres", "", "Rocco Jr.", "Perro - Poodle", "3 años aprox", "8.5", "Mitre 20"])
    # REG-006: Pedro Martinez con letras, Toby
    ws_clientes.append(["REG-006", "Pedro Martinez", "341-abc-1234", "Toby", "Perro - Caniche", "abc", "7 kg", "San Martin 5"])
    # REG-007: sin dueño
    ws_clientes.append(["REG-007", "", "1122334455 / 1155667788", "SinDueno", "Gato - Mestizo", "1 año", "3", "SinDir 1"])
    # REG-008: Laura (sin apellido)
    ws_clientes.append(["REG-008", "Laura", "1144556677", "Mimi", "Gato - Persa", "malo", "sin unidad?", "Rivadavia 100"])
    # REG-009: familia - mismo teléfono que Carlos Gomez pero otro nombre (un solo par)
    ws_clientes.append(["REG-009", "Roberto Diaz", "15-6677-2233", "Luna2", "Perro - Mestizo", "5 años", "10", "Otra 1"])
    # REG-010: revisar - mismo nombre Mimi pero otro teléfono
    ws_clientes.append(["REG-010", "Laura", "1199887766", "Mimi2", "Gato - Persa", "2 años", "4", "Otra 2"])

    # Fila totalmente vacía
    ws_clientes.append(["", "", "", "", "", "", "", ""])

    # Atenciones_Clinicas
    ws_atenciones = wb.create_sheet("Atenciones_Clinicas")
    headers_atenciones = [
        "Nro_Ficha",
        "Fecha_Visita",
        "Paciente_Mascota",
        "Duenio_Referencia",
        "Tipo_Servicio",
        "Detalle_Clinico_y_Cobro",
        "Veterinario_Tratante",
    ]
    ws_atenciones.append(headers_atenciones)
    ws_atenciones.append(["F-001", "11/05/2026", "Firulais", "Juan Perez", "Consulta", "Control", "Dr. Pablo Ramirez"])
    ws_atenciones.append(["F-002", "2026-05-12", "Chicho", "Maria Lopez", "Vacuna", "Vacuna antirrábica", "Dra. Laura"])  # veterinario sin apellido
    # Luna no está en padrón -> huérfana
    ws_atenciones.append(["F-003", "12 de mayo 2026", "Luna", "Carlos Gomez", "Consulta", "Adeuda 500 pesos", "Dr. Pablo Ramirez"])
    ws_atenciones.append(["F-004", "15/05/2026", "Titan", "Carlos Gomez", "Consulta", "Control", "Dr. Pablo Ramirez"])
    ws_atenciones.append(["F-005", "16/05/2026", "Rocco Jr.", "Ana Torres", "Consulta", "Control", "Dr. Martin"])

    # Guarderia_y_Estadias
    ws_guarderia = wb.create_sheet("Guarderia_y_Estadias")
    headers_guarderia = [
        "Nro_Reserva",
        "Mascota",
        "Tutor",
        "Fecha_Ingreso",
        "Fecha_Egreso",
        "Modalidad",
        "Tarifa_Total",
        "Estado_Pago",
        "Comportamiento_Cuidados",
    ]
    ws_guarderia.append(headers_guarderia)
    from datetime import datetime
    # "2026/05/10 00:00:00" es texto -> no_encaja
    ws_guarderia.append(["R-001", "Luna", "Carlos Gomez", "2026/05/10 00:00:00", "13/05/26", "Día", "1000", "Seña", "Tranquilo"])
    # Fecha nativa datetime en una fila existente
    ws_guarderia.append(["R-002", "Toby", "Pedro Martinez", datetime(2026, 6, 1), "2026-06-02", "Noche", "800", "Pago", "Juguetón"])
    ws_guarderia.append(["R-003", "Firulais", "Juan Perez", "01/07/2026", "02/07/2026", "Día", "500", "Pago", "Bien"])
    # agregar filas para cubrir formatos distintos
    ws_guarderia.append(["R-004", "Milo", "Ana Torres", "12 de Mayo 2026", "12/05/2026", "Día", "100", "Pago", "Bien"])
    ws_guarderia.append(["R-005", "Nina", "Ana Torres", "16/05/26", "17/05/26", "Día", "100", "Pago", "Bien"])

    from datetime import datetime as _dt

    wb.properties.modified = _dt(2026, 10, 27, 10, 0, 0)

    ruta = tmp_path / "excel_ficticio_t15.xlsx"
    wb.save(str(ruta))
    wb.close()
    return ruta
