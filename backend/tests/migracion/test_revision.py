"""Archivo de revisión y motivos de revisión de la carga (T-16, RN-05, RN-08)."""

from __future__ import annotations

import csv
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.padron import models as padron_models
from tests.migracion.conftest import crear_excel

ENCABEZADO_REVISION = (
    "hoja,fila,id_origen,campo,valor_original,motivo,accion_sugerida,decision"
)


def _escribir_decision(ruta: Path, decision: str) -> None:
    """Simula la decisión que carga una persona en el CSV de revisión."""
    with ruta.open(encoding="utf-8-sig", newline="") as archivo:
        lector = csv.DictReader(archivo)
        columnas = list(lector.fieldnames or [])
        filas = list(lector)
    filas[0]["decision"] = decision
    with ruta.open("w", encoding="utf-8-sig", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=columnas, lineterminator="\n")
        escritor.writeheader()
        escritor.writerows(filas)


def test_revision_csv_columnas_bom_y_decision_conservada(
    tmp_path, fecha_corte, cargar, leer_revision, fila_cliente
):
    excel = crear_excel(
        tmp_path / "revision.xlsx",
        (
            fila_cliente(id_registro="REG-001", especie="conejo"),
            fila_cliente(id_registro="REG-002", edad="no sé"),
        ),
    )
    salida = tmp_path / "salida"

    reporte = cargar(excel, salida=salida)

    ruta = salida / "revision.csv"
    assert ruta.read_bytes().startswith(b"\xef\xbb\xbf")
    assert ruta.read_text(encoding="utf-8-sig").splitlines()[0] == ENCABEZADO_REVISION
    filas = leer_revision(salida)
    assert [fila["motivo"] for fila in filas] == [
        "especie_no_deducible",
        "edad_no_reconocida",
    ]
    assert [fila["fila"] for fila in filas] == ["2", "3"]
    assert all(fila["decision"] == "" for fila in filas)

    _escribir_decision(ruta, "COMPLETAR")

    segunda = cargar(excel, salida=salida)

    assert segunda.a_revision == reporte.a_revision
    assert [fila["decision"] for fila in leer_revision(salida)] == ["COMPLETAR", ""]
    assert ruta.read_text(encoding="utf-8-sig").splitlines()[0] == ENCABEZADO_REVISION


def test_simulacion_escribe_revision_simulada(
    tmp_path, fecha_corte, cargar, leer_revision, fila_cliente
):
    excel = crear_excel(
        tmp_path / "revision.xlsx", (fila_cliente(especie="conejo"),)
    )
    salida = tmp_path / "salida"

    cargar(excel, salida=salida, simular=True)

    simulada = salida / "revision_simulada.csv"
    assert simulada.is_file()
    assert not (salida / "revision.csv").exists()
    assert simulada.read_bytes().startswith(b"\xef\xbb\xbf")
    assert [fila["motivo"] for fila in leer_revision(salida, simular=True)] == [
        "especie_no_deducible"
    ]


def test_sin_apellido_sin_dni_y_sin_telefono(
    tmp_path, fecha_corte, cargar, contar, personas, registro, engine_sqlite, fila_cliente
):
    excel = crear_excel(
        tmp_path / "personas.xlsx",
        (
            fila_cliente(id_registro="REG-001", nombre="Lucia", mascota="Titan"),
            fila_cliente(
                id_registro="REG-002",
                nombre="ANA LOPEZ",
                telefono="11 4444-1111",
                mascota="Rocco",
            ),
            fila_cliente(
                id_registro="REG-003",
                nombre="BETO DIAZ",
                telefono="Sin telefono (dejo mail)",
                mascota="Toby",
            ),
        ),
    )

    reporte = cargar(excel)

    assert dict(reporte.a_revision) == {"persona_sin_apellido": 1}
    assert reporte.cargadas == 2
    fila_revisada = registro(2)
    assert fila_revisada is not None
    assert fila_revisada["estado"] == "REVISION"
    assert [persona["apellido"] for persona in personas()] == ["Lopez", "Diaz"]
    assert contar(padron_models.Paciente) == 2
    assert contar(padron_models.Telefono) == 1
    with Session(bind=engine_sqlite) as db:
        personas_db = list(db.execute(select(padron_models.Persona)).scalars())
    assert [persona.dni for persona in personas_db] == [None, None]


def test_duenio_de_un_solo_termino_y_mascotas_del_mismo_duenio(
    tmp_path,
    fecha_corte,
    cargar,
    contar,
    pacientes,
    engine_sqlite,
    fila_cliente,
):
    solo_nombre = crear_excel(
        tmp_path / "lucia.xlsx",
        (fila_cliente(id_registro="REG-001", nombre="Lucia", mascota="Titan"),),
    )

    cargar(solo_nombre)

    assert contar(padron_models.Persona) == 0
    assert contar(padron_models.Paciente) == 0

    con_apellido = crear_excel(
        tmp_path / "ana.xlsx",
        (
            fila_cliente(id_registro="REG-010", nombre="ANA LOPEZ", mascota="Chicho"),
            fila_cliente(id_registro="REG-011", nombre="ANA LOPEZ", mascota="Titan"),
            fila_cliente(id_registro="REG-012", nombre="ANA LOPEZ", mascota="Rocco Jr."),
            fila_cliente(id_registro="REG-013", nombre="ANA LOPEZ", mascota="Rocco"),
        ),
    )

    reporte = cargar(con_apellido)

    assert reporte.cargadas == 4
    assert contar(padron_models.Persona) == 1
    assert contar(padron_models.Paciente) == 4
    assert sorted(paciente["nombre"] for paciente in pacientes()) == [
        "Chicho",
        "Rocco",
        "Rocco Jr.",
        "Titan",
    ]
    with Session(bind=engine_sqlite) as db:
        titulares = {
            titular.persona_id
            for titular in db.execute(select(padron_models.Titularidad)).scalars()
        }
    assert len(titulares) == 1


def test_motivos_de_revision_y_fila_vacia(
    tmp_path, fecha_corte, cargar, contar, fila_cliente
):
    excel = crear_excel(
        tmp_path / "motivos.xlsx",
        (
            fila_cliente(id_registro="REG-001"),
            fila_cliente(id_registro="REG-002", especie="Mestizo mediano"),
            fila_cliente(id_registro="REG-003", edad="no sé"),
            fila_cliente(id_registro="REG-004", peso="80 kg"),
            ("", "", "", "", "", "", "", ""),
        ),
    )

    reporte = cargar(excel)

    assert reporte.leidas == 4
    assert reporte.cargadas == 1
    assert dict(reporte.a_revision) == {
        "especie_no_deducible": 1,
        "edad_no_reconocida": 1,
        "peso_fuera_de_rango": 1,
    }
    assert contar(padron_models.Persona) == 1
    assert contar(padron_models.Paciente) == 1
