"""Deduplicación y peso en la carga del padrón (T-16, RN-06 y RN-50)."""

from __future__ import annotations

from decimal import Decimal

from app.modules.padron import models as padron_models
from tests.migracion.conftest import crear_excel


def test_mismo_telefono_y_nombre_con_dos_mascotas(
    tmp_path, fecha_corte, cargar, contar, personas, pacientes, fila_cliente
):
    excel = crear_excel(
        tmp_path / "dos_mascotas.xlsx",
        (
            fila_cliente(mascota="Firulais", peso="28 kg"),
            fila_cliente(
                id_registro="REG-002",
                nombre="valeria gomez",
                mascota="Mora",
                peso="9 kg",
            ),
        ),
    )

    reporte = cargar(excel)

    assert reporte.cargadas == 2
    assert reporte.errores == 0
    assert reporte.mascotas_existentes == 0
    assert contar(padron_models.Persona) == 1
    assert contar(padron_models.Paciente) == 2
    assert contar(padron_models.Telefono) == 1
    assert [persona["nombre"] for persona in personas()] == ["Valeria"]
    assert sorted(paciente["nombre"] for paciente in pacientes()) == ["Firulais", "Mora"]


def test_mismo_nombre_con_otro_telefono_va_a_revision(
    tmp_path, fecha_corte, cargar, contar, personas, pacientes, leer_revision, fila_cliente
):
    excel = crear_excel(
        tmp_path / "otro_telefono.xlsx",
        (
            fila_cliente(),
            fila_cliente(
                id_registro="REG-002",
                nombre="VALERIA GOMEZ",
                telefono="11 9999-0000",
                mascota="Mora",
            ),
        ),
    )

    reporte = cargar(excel)

    valeria = personas()[0]
    assert reporte.cargadas == 1
    assert dict(reporte.a_revision) == {"nombre_con_otro_telefono": 1}
    assert contar(padron_models.Persona) == 1
    assert contar(padron_models.Telefono) == 1
    assert [paciente["nombre"] for paciente in pacientes()] == ["Firulais"]
    assert leer_revision() == [
        {
            "hoja": "Clientes_y_Mascotas",
            "fila": "3",
            "id_origen": "REG-002",
            "campo": "Telefono_Contacto",
            "valor_original": "11 9999-0000",
            "motivo": "nombre_con_otro_telefono",
            "accion_sugerida": f"ASOCIAR_A:{valeria['id']}",
            "decision": "",
        }
    ]


def test_mismo_telefono_con_otro_nombre_va_a_revision(
    tmp_path, fecha_corte, cargar, contar, personas, pacientes, leer_revision, fila_cliente
):
    excel = crear_excel(
        tmp_path / "otro_nombre.xlsx",
        (
            fila_cliente(nombre="ANA LOPEZ", telefono="11 4444-1111", mascota="Rocco"),
            fila_cliente(
                id_registro="REG-002",
                nombre="BETO DIAZ",
                telefono="11 4444-1111",
                mascota="Toby",
            ),
        ),
    )

    reporte = cargar(excel)

    ana = personas()[0]
    assert reporte.cargadas == 1
    assert dict(reporte.a_revision) == {"telefono_de_otra_persona": 1}
    assert contar(padron_models.Persona) == 1
    assert [paciente["nombre"] for paciente in pacientes()] == ["Rocco"]
    revision = leer_revision()
    assert len(revision) == 1
    assert revision[0]["motivo"] == "telefono_de_otra_persona"
    assert revision[0]["accion_sugerida"] == f"ASOCIAR_A:{ana['id']}"


def test_peso_posterior_gana_y_el_reporte_lista_ambas_filas(
    tmp_path, fecha_corte, cargar, contar, pacientes, fila_cliente
):
    excel = crear_excel(
        tmp_path / "peso.xlsx",
        (
            fila_cliente(mascota="Firulais", peso="10 kg"),
            fila_cliente(
                id_registro="REG-002",
                nombre="valeria gomez",
                mascota="Firulais",
                peso="12 kg",
            ),
        ),
    )

    reporte = cargar(excel)

    assert reporte.cargadas == 2
    assert reporte.mascotas_existentes == 1
    assert len(reporte.conflictos_peso) == 1
    conflicto = reporte.conflictos_peso[0]
    assert (conflicto.fila_anterior, conflicto.fila_nueva) == (2, 3)
    assert contar(padron_models.Paciente) == 1
    assert Decimal(str(pacientes()[0]["peso_kg"])) == Decimal("12")
