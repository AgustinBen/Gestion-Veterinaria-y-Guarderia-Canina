"""Idempotencia, transacción por fila y simulación de la carga (T-16, RN-50)."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from app.core.parametros import ParametroNoDefinido
from app.modules.migracion import carga as carga_mod
from app.modules.migracion.carga import ReporteCarga
from app.modules.migracion.models import MigracionRegistro
from app.modules.padron import models as padron_models
from app.modules.padron.service import DatosInvalidos
from tests.migracion.conftest import crear_excel


def _conteos(reporte: ReporteCarga) -> dict[str, object]:
    """Solo conteos: la simulación y la carga real deben coincidir en esto."""
    return {
        "leidas": reporte.leidas,
        "cargadas": reporte.cargadas,
        "ya_cargadas": reporte.ya_cargadas,
        "cambiadas": reporte.cambiadas,
        "mascotas_existentes": reporte.mascotas_existentes,
        "a_revision": dict(reporte.a_revision),
        "errores": reporte.errores,
        "conflictos_peso": len(reporte.conflictos_peso),
    }


def test_sin_fecha_corte_falla_antes_de_escribir(tmp_path, cargar, contar, fila_cliente):
    excel = crear_excel(tmp_path / "unico.xlsx", (fila_cliente(),))

    with pytest.raises(ParametroNoDefinido):
        cargar(excel)

    assert contar(padron_models.Persona) == 0
    assert contar(padron_models.Paciente) == 0
    assert contar(MigracionRegistro) == 0
    assert not (tmp_path / "salida").exists()


def test_segunda_corrida_no_duplica(tmp_path, fecha_corte, cargar, contar, fila_cliente):
    excel = crear_excel(
        tmp_path / "clientes.xlsx",
        (
            fila_cliente(),
            fila_cliente(
                id_registro="REG-002",
                nombre="MARCOS PEREZ",
                telefono="11 6677-2233",
                mascota="Chicho",
            ),
        ),
    )
    primera = cargar(excel)
    assert primera.cargadas == 2
    assert primera.ya_cargadas == 0
    antes = (
        contar(padron_models.Persona),
        contar(padron_models.Paciente),
        contar(MigracionRegistro),
    )
    assert antes == (2, 2, 2)

    segunda = cargar(excel)

    assert segunda.cargadas == 0
    assert segunda.ya_cargadas == 2
    assert segunda.errores == 0
    despues = (
        contar(padron_models.Persona),
        contar(padron_models.Paciente),
        contar(MigracionRegistro),
    )
    assert despues == antes


def test_contenido_cambiado_se_reporta_y_no_pisa(
    tmp_path, fecha_corte, cargar, registro, pacientes, fila_cliente
):
    cargar(crear_excel(tmp_path / "v1.xlsx", (fila_cliente(peso="10 kg"),)))
    original = registro(2)
    assert original is not None
    assert original["estado"] == "CARGADA"

    reporte = cargar(
        crear_excel(
            tmp_path / "v2.xlsx",
            (fila_cliente(mascota="Firulais II", peso="30 kg"),),
        )
    )

    assert reporte.cambiadas == 1
    assert reporte.cargadas == 0
    assert [paciente["nombre"] for paciente in pacientes()] == ["Firulais"]
    assert Decimal(str(pacientes()[0]["peso_kg"])) == Decimal("10")
    assert registro(2) == original


def test_falla_despues_de_crear_la_persona_no_deja_huerfana(
    tmp_path,
    fecha_corte,
    cargar,
    contar,
    registro,
    personas,
    pacientes,
    fila_cliente,
    monkeypatch,
):
    excel = crear_excel(
        tmp_path / "dos.xlsx",
        (
            fila_cliente(nombre="ANA LOPEZ", telefono="11 4444-1111", mascota="Rocco"),
            fila_cliente(
                id_registro="REG-002",
                nombre="BETO DIAZ",
                telefono="11 5555-2222",
                mascota="Toby",
            ),
        ),
    )
    original = carga_mod._resolver_mascota

    def rota(db, fila, *args, **kwargs):
        if fila.numero == 2:
            raise RuntimeError("falla forzada")
        return original(db, fila, *args, **kwargs)

    monkeypatch.setattr(carga_mod, "_resolver_mascota", rota)

    reporte = cargar(excel)

    assert reporte.errores == 1
    assert reporte.cargadas == 1
    fila_rota = registro(2)
    assert fila_rota is not None
    assert fila_rota["estado"] == "ERROR"
    assert "RuntimeError" in str(fila_rota["motivo"])
    assert [persona["apellido"] for persona in personas()] == ["Diaz"]
    assert [paciente["nombre"] for paciente in pacientes()] == ["Toby"]
    assert contar(MigracionRegistro) == 2


def test_revision_despues_de_crear_la_persona_no_deja_huerfana(
    tmp_path,
    fecha_corte,
    cargar,
    registro,
    personas,
    pacientes,
    fila_cliente,
    monkeypatch,
):
    excel = crear_excel(
        tmp_path / "dos.xlsx",
        (
            fila_cliente(nombre="ANA LOPEZ", telefono="11 4444-1111", mascota="Rocco"),
            fila_cliente(
                id_registro="REG-002",
                nombre="BETO DIAZ",
                telefono="11 5555-2222",
                mascota="Toby",
            ),
        ),
    )
    original = carga_mod._resolver_mascota

    def revisa(db, fila, *args, **kwargs):
        if fila.numero == 2:
            raise DatosInvalidos("dato forzado")
        return original(db, fila, *args, **kwargs)

    monkeypatch.setattr(carga_mod, "_resolver_mascota", revisa)

    reporte = cargar(excel)

    assert dict(reporte.a_revision) == {"datos_invalidos": 1}
    assert reporte.errores == 0
    assert reporte.cargadas == 1
    fila_revisada = registro(2)
    assert fila_revisada is not None
    assert fila_revisada["estado"] == "REVISION"
    assert [persona["apellido"] for persona in personas()] == ["Diaz"]
    assert [paciente["nombre"] for paciente in pacientes()] == ["Toby"]


def test_simulacion_no_escribe_ni_pisa_los_archivos(
    tmp_path, fecha_corte, cargar, contar, fila_cliente, leer_revision
):
    excel = crear_excel(
        tmp_path / "clientes.xlsx",
        (
            fila_cliente(),
            fila_cliente(
                id_registro="REG-002",
                nombre="ANA LOPEZ",
                telefono="11 4444-1111",
                mascota="Rocco",
            ),
            fila_cliente(
                id_registro="REG-003",
                nombre="MARCOS PEREZ",
                telefono="11 6677-2233",
                mascota="Chicho",
                especie="conejo",
            ),
        ),
    )
    salida = tmp_path / "reportes"

    simulada = cargar(excel, simular=True, salida=salida)

    assert simulada.simulacion is True
    assert contar(padron_models.Persona) == 0
    assert contar(padron_models.Paciente) == 0
    assert contar(MigracionRegistro) == 0
    assert not (salida / "reporte_carga.json").exists()
    assert not (salida / "revision.csv").exists()
    assert (salida / "reporte_carga_simulado.json").is_file()
    assert len(leer_revision(salida, simular=True)) == 1

    real = cargar(excel, salida=salida)
    assert _conteos(real) == _conteos(simulada)
    assert real.cargadas == 2
    assert dict(real.a_revision) == {"especie_no_deducible": 1}

    reporte_json = (salida / "reporte_carga.json").read_text(encoding="utf-8")
    revision_csv = (salida / "revision.csv").read_text(encoding="utf-8")
    antes = (
        contar(padron_models.Persona),
        contar(padron_models.Paciente),
        contar(MigracionRegistro),
    )

    cargar(excel, simular=True, salida=salida)

    assert (salida / "reporte_carga.json").read_text(encoding="utf-8") == reporte_json
    assert (salida / "revision.csv").read_text(encoding="utf-8") == revision_csv
    despues = (
        contar(padron_models.Persona),
        contar(padron_models.Paciente),
        contar(MigracionRegistro),
    )
    assert despues == antes
    assert Path(salida / "reporte_carga_simulado.json").is_file()

