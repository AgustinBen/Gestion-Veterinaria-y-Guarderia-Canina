"""Reporte JSON, consola y texto original de la carga (T-16, RN-50)."""

from __future__ import annotations

import json
from collections import Counter

from app.modules.migracion.carga import (
    ConflictoPeso,
    ReporteCarga,
    resumen_consola,
)
from tests.migracion.conftest import crear_excel

CLAVES_REPORTE = {
    "simulacion",
    "hoja",
    "leidas",
    "cargadas",
    "ya_cargadas",
    "cambiadas",
    "mascotas_existentes",
    "a_revision",
    "conflictos_peso",
    "errores",
}


def test_reporte_json_determinista_y_con_claves(
    tmp_path, fecha_corte, cargar, fila_cliente
):
    excel = crear_excel(
        tmp_path / "reporte.xlsx",
        (
            fila_cliente(id_registro="REG-001"),
            fila_cliente(id_registro="REG-002", especie="conejo"),
        ),
    )
    salida = tmp_path / "salida"

    cargar(excel, salida=salida, simular=True)
    simulada = salida / "reporte_carga_simulado.json"
    primera_simulacion = simulada.read_text(encoding="utf-8")
    cargar(excel, salida=salida, simular=True)
    assert simulada.read_text(encoding="utf-8") == primera_simulacion

    real = cargar(excel, salida=salida)
    contenido = (salida / "reporte_carga.json").read_text(encoding="utf-8")
    assert contenido == (
        json.dumps(real.a_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    datos = json.loads(contenido)
    assert set(datos) == CLAVES_REPORTE
    assert datos["simulacion"] is False
    assert datos["hoja"] == "Clientes_y_Mascotas"
    assert datos["leidas"] == 2
    assert datos["cargadas"] == 1
    assert datos["ya_cargadas"] == 0
    assert datos["cambiadas"] == 0
    assert datos["mascotas_existentes"] == 0
    assert datos["a_revision"] == {"especie_no_deducible": 1}
    assert datos["conflictos_peso"] == []
    assert datos["errores"] == 0

    segunda = cargar(excel, salida=salida)
    datos_segunda = json.loads(
        (salida / "reporte_carga.json").read_text(encoding="utf-8")
    )
    assert segunda.cargadas == 0
    assert set(datos_segunda) == CLAVES_REPORTE
    assert datos_segunda["leidas"] == datos["leidas"]
    assert datos_segunda["cambiadas"] == datos["cambiadas"]
    assert datos_segunda["a_revision"] == datos["a_revision"]
    assert datos_segunda["errores"] == datos["errores"]
    assert datos_segunda["cargadas"] == 0
    assert datos_segunda["ya_cargadas"] == 1


def test_resumen_consola_solo_conteos(tmp_path, fecha_corte, cargar, fila_cliente):
    reporte = ReporteCarga(
        leidas=5,
        cargadas=2,
        ya_cargadas=1,
        cambiadas=1,
        mascotas_existentes=1,
        errores=1,
        a_revision=Counter({"especie_no_deducible": 2}),
        conflictos_peso=[
            ConflictoPeso(
                paciente_id=1,
                fila_anterior=2,
                fila_nueva=4,
                peso_anterior="10.00",
                peso_nuevo="12.00",
            )
        ],
    )

    assert resumen_consola(reporte) == (
        "Carga completada.\n"
        "Filas leídas: 5\n"
        "Cargadas: 2\n"
        "Ya cargadas (se saltearon): 1\n"
        "Cambiadas (no se pisaron): 1\n"
        "Mascotas ya existentes: 1\n"
        "A revisión: 2\n"
        "Errores: 1\n"
        "Revisión por motivo: especie_no_deducible=2\n"
        "Conflictos de peso: 1"
    )
    assert "no se escribió en la base" in resumen_consola(
        ReporteCarga(simulacion=True)
    )

    excel = crear_excel(
        tmp_path / "datos.xlsx",
        (fila_cliente(nombre="VALERIA GOMEZ", telefono="11 4455-8899"),),
    )
    real = resumen_consola(cargar(excel))
    assert "VALERIA" not in real.upper()
    assert "GOMEZ" not in real.upper()
    assert "4455" not in real
    assert "Cargadas: 1" in real


def test_texto_original_conserva_los_valores_crudos(
    tmp_path, fecha_corte, cargar, registro, fila_cliente
):
    cruda = (
        "REG-900",
        "valeria  GOMEZ",
        "11 4455-8899",
        "Firulais",
        "Perro - Mestizo",
        "4 años",
        "28,5 kg",
        "Av. Siempre Viva 742",
    )
    revisada = (
        "REG-901",
        "BETO DIAZ",
        "11 5555-2222",
        "Toby",
        "conejo",
        "2 años",
        "5 kg",
        "Calle 2",
    )
    excel = crear_excel(tmp_path / "crudo.xlsx", (cruda, revisada))

    cargar(excel)

    cargada = registro(2)
    assert cargada is not None
    assert cargada["estado"] == "CARGADA"
    assert json.loads(str(cargada["texto_original"])) == {
        "hoja": "Clientes_y_Mascotas",
        "fila": 2,
        "valores": {
            "ID_Registro": "REG-900",
            "Nombre_Duenio": "valeria  GOMEZ",
            "Telefono_Contacto": "11 4455-8899",
            "Nombre_Mascota": "Firulais",
            "Especie_Raza": "Perro - Mestizo",
            "Edad_Aprox": "4 años",
            "Peso_Kg": "28,5 kg",
            "Direccion_Localidad": "Av. Siempre Viva 742",
        },
    }

    en_revision = registro(3)
    assert en_revision is not None
    assert en_revision["estado"] == "REVISION"
    valores = json.loads(str(en_revision["texto_original"]))["valores"]
    assert valores["Especie_Raza"] == "conejo"
    assert valores["Nombre_Duenio"] == "BETO DIAZ"
    assert valores["Peso_Kg"] == "5 kg"
