from __future__ import annotations

import hashlib
from pathlib import Path

from app.modules.migracion import lector, perfilado


def _hash_archivo(ruta: Path) -> str:
    h = hashlib.sha256()
    h.update(ruta.read_bytes())
    return h.hexdigest()


def test_filas_por_hoja_valores_literales(excel_ficticio_t15: Path, tmp_path: Path):
    reporte = perfilado.perfilar_excel(excel_ficticio_t15, tmp_path / "salida")
    assert reporte["conteo_filas_por_hoja"]["Clientes_y_Mascotas"] == 11
    assert reporte["conteo_filas_por_hoja"]["Atenciones_Clinicas"] == 5
    assert reporte["conteo_filas_por_hoja"]["Guarderia_y_Estadias"] == 5


def test_fechas_por_formato_y_nativa(excel_ficticio_t15: Path, tmp_path: Path):
    reporte = perfilado.perfilar_excel(excel_ficticio_t15, tmp_path / "salida")
    assert reporte["fechas"]["nativas"] == 1
    assert reporte["fechas"]["no_encaja"] >= 1


def test_telefonos_separados(excel_ficticio_t15: Path, tmp_path: Path):
    reporte = perfilado.perfilar_excel(excel_ficticio_t15, tmp_path / "salida")
    assert reporte["telefonos"]["formatos_distintos_mismo_numero"] == 1
    assert reporte["telefonos"]["vacios"] == 1
    assert reporte["telefonos"]["con_letras"] == 1
    # varios_numeros_en_celda contado por separado
    assert isinstance(reporte["telefonos"]["varios_numeros_en_celda"], int)


def test_duplicados_tres_listas(excel_ficticio_t15: Path, tmp_path: Path):
    reporte = perfilado.perfilar_excel(excel_ficticio_t15, tmp_path / "salida")
    assert len(reporte["duplicados"]["misma_persona"]) == 1
    assert len(reporte["duplicados"]["revisar"]) == 1
    assert len(reporte["duplicados"]["familia"]) == 1
    assert (len(reporte["duplicados"]["misma_persona"]) + len(reporte["duplicados"]["revisar"])) == 2


def test_sin_apellido_listas_separadas(excel_ficticio_t15: Path, tmp_path: Path):
    reporte = perfilado.perfilar_excel(excel_ficticio_t15, tmp_path / "salida")
    assert len(reporte["sin_apellido"]["duenios"]) >= 1
    assert len(reporte["sin_apellido"]["veterinarios"]) >= 1


def test_huerfanas_y_rocco_jr_no_huerfano(excel_ficticio_t15: Path, tmp_path: Path):
    reporte = perfilado.perfilar_excel(excel_ficticio_t15, tmp_path / "salida")
    mascotas_huerfanas_str = str(reporte["mascotas_sin_duenio"]).lower()
    assert "chicho" not in mascotas_huerfanas_str
    assert "titan" not in mascotas_huerfanas_str
    assert "rocco" not in mascotas_huerfanas_str
    assert len(reporte["mascotas_sin_duenio"]) == 3


def test_dni_columna_inexistente(excel_ficticio_t15: Path, tmp_path: Path):
    reporte = perfilado.perfilar_excel(excel_ficticio_t15, tmp_path / "salida")
    assert reporte["dni"]["columna_inexistente"] is True
    assert reporte["dni"]["sin_dni"] == 10


def test_fecha_ultima_edicion_y_conteos(excel_ficticio_t15: Path, tmp_path: Path):
    reporte = perfilado.perfilar_excel(excel_ficticio_t15, tmp_path / "salida")
    assert "fecha_ultima_edicion" in reporte
    assert "conteo_filas_por_hoja" in reporte


def test_filas_vacias_no_cuentan_como_persona(excel_ficticio_t15: Path, tmp_path: Path):
    reporte = perfilado.perfilar_excel(excel_ficticio_t15, tmp_path / "salida")
    assert len(reporte["filas_totalmente_vacias"]) == 1
    assert reporte["dni"]["sin_dni"] == 10


def test_deuda_en_texto_indicio(excel_ficticio_t15: Path, tmp_path: Path):
    reporte = perfilado.perfilar_excel(excel_ficticio_t15, tmp_path / "salida")
    assert len(reporte["deuda_en_el_texto"]) == 1


def test_archivos_se_escriben_y_dos_corridas_comparan_contenido(excel_ficticio_t15: Path, tmp_path: Path):
    hash_antes = _hash_archivo(excel_ficticio_t15)
    salida1 = tmp_path / "salida1"
    salida2 = tmp_path / "salida2"
    perfilado.perfilar_excel(excel_ficticio_t15, salida1)
    perfilado.perfilar_excel(excel_ficticio_t15, salida2)
    hash_despues = _hash_archivo(excel_ficticio_t15)
    assert hash_antes == hash_despues
    json1 = (salida1 / "perfilado.json").read_text(encoding="utf-8")
    csv1 = (salida1 / "perfilado_filas.csv").read_text(encoding="utf-8")
    json2 = (salida2 / "perfilado.json").read_text(encoding="utf-8")
    csv2 = (salida2 / "perfilado_filas.csv").read_text(encoding="utf-8")
    assert json1 == json2
    assert csv1 == csv2
    # verificar que se escriben
    assert (salida1 / "perfilado.json").exists()
    assert (salida1 / "perfilado_filas.csv").exists()


def test_hoja_faltante_excepcion_propia(tmp_path: Path):
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "OtraHoja"
    ws.append(["a"])
    ruta = tmp_path / "mal.xlsx"
    wb.save(str(ruta))
    wb.close()
    try:
        import pytest

        with pytest.raises(lector.HojaFaltanteError):
            perfilado.perfilar_excel(ruta, tmp_path / "out")
    except ImportError:
        import pytest

        with pytest.raises(lector.HojaFaltanteError):
            perfilado.perfilar_excel(ruta, tmp_path / "out")


def test_columna_renombrada_excepcion_propia(excel_ficticio_t15: Path, tmp_path: Path):
    import pytest
    from openpyxl import load_workbook

    wb = load_workbook(str(excel_ficticio_t15))
    ws = wb["Clientes_y_Mascotas"]
    ws["A1"].value = "ID_REGISTRO_CAMBIADO"
    ruta = tmp_path / "mal2.xlsx"
    wb.save(str(ruta))
    wb.close()
    with pytest.raises(lector.ColumnaFaltanteError):
        perfilado.perfilar_excel(ruta, tmp_path / "out2")
