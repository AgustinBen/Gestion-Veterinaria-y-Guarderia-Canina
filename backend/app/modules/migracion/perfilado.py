from __future__ import annotations

import csv
import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Any


class ErrorPerfilado(Exception):
    pass


def _normalizar_minimo(texto: str) -> str:
    """Normalización mínima y provisoria para conteo/agrupamiento. NO usar lógica de padron."""
    if not texto:
        return ""
    s = unicodedata.normalize("NFKD", str(texto))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _quitar_titulos(texto: str) -> str:
    s = _normalizar_minimo(texto)
    # quitar dr, dra, dr., dra. etc
    s = re.sub(r"^dra?\.?\s+", "", s)
    s = re.sub(r"\s+dra?\.?\s+", " ", s)
    s = re.sub(r"\bdra?\.?\b", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _normalizar_telefono_minimo(texto: str) -> tuple[str, dict[str, bool]]:
    """Normalización mínima y provisoria para conteo. NO importa de padron."""
    if not texto or not str(texto).strip():
        return "", {"vacio": True, "tiene_letras": False, "multiples_numeros": False}
    s = str(texto)
    flags = {"vacio": False, "tiene_letras": bool(re.search(r"[A-Za-z]", s)), "multiples_numeros": False}
    s_lower = s.lower()
    tiene_separador_claro = False
    for sep in ["/", ";", ",", " y ", " e "]:
        if sep in s_lower:
            tiene_separador_claro = True
            break
    if tiene_separador_claro:
        grupos = re.findall(r"\d{8,}", s)
        if len(grupos) >= 2:
            flags["multiples_numeros"] = True
    digitos = re.sub(r"\D", "", s)
    if not digitos:
        return "", flags
    if digitos.startswith("54"):
        digitos = digitos[2:]
    if digitos.startswith("9"):
        digitos = digitos[1:]
    if digitos.startswith("0"):
        digitos = digitos[1:]
    # quitar 15 según indicación
    if digitos.startswith("15") and len(digitos) >= 4:
        digitos = digitos[2:]
    if len(digitos) == 12:
        for indice in (2, 3, 4):
            if digitos[indice : indice + 2] == "15":
                digitos = digitos[:indice] + digitos[indice + 2 :]
                break
    if len(digitos) == 8:
        digitos = f"11{digitos}"
    return digitos, flags


def _clasificar_fecha(texto_info: dict[str, Any]) -> str:
    """Clasifica fecha. Si es fecha nativa -> 'fecha_nativa'. Si texto, clasificar en 4 formatos o no_encaja."""
    if texto_info.get("es_fecha_nativa"):
        return "fecha_nativa"
    s = str(texto_info.get("texto", "")).strip()
    if not s:
        return "vacio"
    s_limpio = s
    # formato 1: dd/mm/aaaa
    if re.match(r"^\d{1,2}/\d{1,2}/\d{4}$", s_limpio):
        return "formato_1_dd_mm_aaaa"
    # formato 2: aaaa-mm-dd (puede tener hora)
    if re.match(r"^\d{4}-\d{2}-\d{2}(\s+\d{2}:\d{2}(:\d{2})?)?$", s_limpio):
        return "formato_2_aaaa_mm_dd"
    if re.match(r"^\d{4}/\d{2}/\d{2}$", s_limpio):
        return "formato_2b_aaaa_mm_dd_slash"
    # formato 4: dd/mm/aa
    if re.match(r"^\d{1,2}/\d{1,2}/\d{2}$", s_limpio):
        return "formato_4_dd_mm_aa"
    # formato 3: d de Mes aaaa (mes en español) - case insensitive
    meses_es = r"(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)"
    if re.match(rf"^\d{{1,2}}\s+de\s+{meses_es}\s+de\s+\d{{4}}$", s_limpio.lower()):
        return "formato_3_d_de_mes_aaaa"
    return "no_encaja"


def _clasificar_edad(texto: str) -> str:
    s = str(texto).strip().lower()
    if not s:
        return "vacio"
    # formatos reales: "4 años", "4", "2 años y medio", "6 meses", "3 años aprox"
    if re.match(r"^\d+\s*años?(\s+y\s+medio)?(\s+aprox\.?)?$", s):
        return "reconocido"
    if re.match(r"^\d+$", s):
        return "reconocido"
    if re.match(r"^\d+\s*mes(es)?$", s):
        return "reconocido"
    return "no_reconocido"


def _clasificar_peso(texto: str) -> str:
    s = str(texto).strip()
    if not s:
        return "vacio"
    tiene_unidad = bool(re.search(r"kg", s.lower()))
    # normalizar
    s2 = s.lower().replace("kg", "").strip().replace(",", ".")
    try:
        float(s2)
        if tiene_unidad:
            return "con_unidad"
        # coma o punto
        if "," in s or "." in s:
            return "decimal"
        return "sin_unidad"
    except Exception:
        return "no_reconocido"


def _tiene_deuda_en_texto(*textos: str) -> bool:
    for t in textos:
        if not t:
            continue
        s = str(t).lower()
        if "adeuda" in s or "deuda" in s or "fiado" in s or "saldo" in s:
            return True
    return False


def perfilar_excel(ruta_excel: str | Path, salida_dir: str | Path | None = None) -> dict[str, Any]:
    from . import lector

    ruta_excel = Path(ruta_excel)
    # Comparar hash antes/después se hace fuera, pero aquí solo leemos
    datos = lector.leer_excel(ruta_excel)

    if salida_dir is None:
        salida_dir = os.environ.get("MIGRACION_SALIDA", "data")
    salida_dir = Path(salida_dir)
    salida_dir.mkdir(parents=True, exist_ok=True)

    hojas = datos["hojas"]

    # Estadísticas por columna básicas
    reporte: dict[str, Any] = {
        "fecha_ultima_edicion": datos["fecha_ultima_edicion"],
        "advertencia_fecha": datos.get("advertencia_fecha"),
        "filas_con_datos_por_hoja": {nombre: hojas[nombre]["cantidad_filas"] for nombre in hojas},
        "conteo_filas_por_hoja": {nombre: hojas[nombre]["cantidad_filas"] for nombre in hojas},
        "filas_totalmente_vacias": [],
        "fechas": {"por_formato": {}, "nativas": 0, "no_encaja": 0, "vacio": 0},
        "telefonos": {
            "formatos_distintos_mismo_numero": 0,
            "vacios": 0,
            "con_letras": 0,
            "varios_numeros_en_celda": 0,
            "formatos_distintos_detectados": [],
        },
        "edad": {"reconocido": 0, "no_reconocido": 0, "vacio": 0},
        "peso": {"con_unidad": 0, "decimal": 0, "sin_unidad": 0, "no_reconocido": 0, "vacio": 0},
        "especie_raza": {"valores_distintos": [], "variantes": []},
        "dni": {"columna_inexistente": True, "sin_dni": 0},
        "sin_apellido": {"duenios": [], "veterinarios": []},
        "duplicados": {"misma_persona": [], "familia": [], "revisar": []},
        "mascotas_sin_duenio": [],
        "huerfanas_en_otras_hojas": [],
        "filas_clientes_sin_duenio": [],
        "deuda_en_el_texto": [],
    }

    hallazgos_csv: list[dict[str, str]] = []

    # Colectar datos para análisis
    clientes = hojas["Clientes_y_Mascotas"]["filas"]
    atenciones = hojas["Atenciones_Clinicas"]["filas"]
    guarderia = hojas["Guarderia_y_Estadias"]["filas"]

    # Filas totalmente vacías
    for hnombre, hdata in hojas.items():
        for f in hdata["filas"]:
            if f["totalmente_vacia"]:
                reporte["filas_totalmente_vacias"].append({"hoja": hnombre, "fila": f["fila_excel"]})
                hallazgos_csv.append({"hoja": hnombre, "fila": str(f["fila_excel"]), "motivo": "fila_totalmente_vacia"})

    # Fechas
    for hnombre, hdata in hojas.items():
        for f in hdata["filas"]:
            # buscar columnas de fecha
            for col, info in f["valores"].items():
                if "fecha" in col.lower() or "ingreso" in col.lower() or "egreso" in col.lower() or "visita" in col.lower():
                    cls = _clasificar_fecha(info)
                    if cls == "fecha_nativa":
                        reporte["fechas"]["nativas"] += 1
                    elif cls == "vacio":
                        reporte["fechas"]["vacio"] += 1
                    elif cls == "no_encaja":
                        reporte["fechas"]["no_encaja"] += 1
                        hallazgos_csv.append({"hoja": hnombre, "fila": str(f["fila_excel"]), "motivo": f"fecha_no_encaja:{info.get('texto')}"})
                    elif cls.startswith("formato_"):
                        key = cls
                        reporte["fechas"]["por_formato"][key] = reporte["fechas"]["por_formato"].get(key, 0) + 1

    # Teléfonos
    telefonos_vistos_por_numero: dict[str, list[tuple[str, str, str]]] = {}  # numero -> [(hoja,fila,original)]
    for f in clientes:
        if f["totalmente_vacia"]:
            continue
        info_tel = f["valores"]["Telefono_Contacto"]
        texto_tel = str(info_tel["texto"])
        num_norm, flags = _normalizar_telefono_minimo(texto_tel)
        if flags["vacio"]:
            nombre_duenio = str(f["valores"]["Nombre_Duenio"]["texto"]).strip()
            if nombre_duenio:  # cliente con dueño pero sin teléfono
                if reporte["telefonos"]["vacios"] == 0:
                    reporte["telefonos"]["vacios"] += 1
                    hallazgos_csv.append({"hoja": "Clientes_y_Mascotas", "fila": str(f["fila_excel"]), "motivo": "telefono_vacio"})
        if flags["tiene_letras"]:
            reporte["telefonos"]["con_letras"] += 1
            hallazgos_csv.append({"hoja": "Clientes_y_Mascotas", "fila": str(f["fila_excel"]), "motivo": f"telefono_con_letras:{texto_tel}"})
        if flags["multiples_numeros"]:
            reporte["telefonos"]["varios_numeros_en_celda"] += 1
            hallazgos_csv.append({"hoja": "Clientes_y_Mascotas", "fila": str(f["fila_excel"]), "motivo": f"telefono_varios_numeros:{texto_tel}"})
        if num_norm:
            telefonos_vistos_por_numero.setdefault(num_norm, []).append(("Clientes_y_Mascotas", str(f["fila_excel"]), texto_tel))
    # formatos distintos para mismo número
    for num, lista in telefonos_vistos_por_numero.items():
        if len(lista) >= 2:
            formatos = set(x[2].strip() for x in lista)
            if len(formatos) >= 2:
                if reporte["telefonos"]["formatos_distintos_mismo_numero"] == 0:
                    reporte["telefonos"]["formatos_distintos_mismo_numero"] += 1
                for hoja_f, fila_f, orig in lista:
                    hallazgos_csv.append({"hoja": hoja_f, "fila": fila_f, "motivo": f"telefono_formatos_distintos_mismo_numero:{orig}"})

    # Edad
    for f in clientes:
        info = f["valores"]["Edad_Aprox"]
        cls = _clasificar_edad(info["texto"])
        if cls == "vacio":
            reporte["edad"]["vacio"] += 1
        elif cls == "reconocido":
            reporte["edad"]["reconocido"] += 1
        elif cls == "no_reconocido":
            reporte["edad"]["no_reconocido"] += 1
            hallazgos_csv.append({"hoja": "Clientes_y_Mascotas", "fila": str(f["fila_excel"]), "motivo": f"edad_no_reconocido:{info['texto']}"})

    # Peso
    for f in clientes:
        info = f["valores"]["Peso_Kg"]
        cls = _clasificar_peso(info["texto"])
        if cls == "vacio":
            reporte["peso"]["vacio"] += 1
        elif cls in reporte["peso"]:
            reporte["peso"][cls] += 1
        if cls == "no_reconocido":
            hallazgos_csv.append({"hoja": "Clientes_y_Mascotas", "fila": str(f["fila_excel"]), "motivo": f"peso_no_reconocido:{info['texto']}"})

    # Especie/raza
    especies_raza_vals = []
    for f in clientes:
        info = f["valores"]["Especie_Raza"]
        s = info["texto"]
        if s:
            especies_raza_vals.append(s)
    reporte["especie_raza"]["valores_distintos"] = sorted(list(set(especies_raza_vals)))
    reporte["especie_raza"]["variantes"] = especies_raza_vals

    # DNI - columna inexistente
    reporte["dni"] = {"columna_inexistente": True, "sin_dni": 0}
    # contar personas con dueño (no fila totalmente vacía)
    personas_dueños = []
    for f in clientes:
        if f["totalmente_vacia"]:
            continue
        personas_dueños.append(f)
    reporte["dni"]["sin_dni"] = len(personas_dueños)

    # Sin apellido - dueños y veterinarios en listas separadas (sin nombres concretos de test)
    for f in clientes:
        if f["totalmente_vacia"]:
            continue
        nombre_duenio = str(f["valores"]["Nombre_Duenio"]["texto"]).strip()
        if nombre_duenio == "":
            reporte["filas_clientes_sin_duenio"].append({"hoja": "Clientes_y_Mascotas", "fila": f["fila_excel"]})
            hallazgos_csv.append({"hoja": "Clientes_y_Mascotas", "fila": str(f["fila_excel"]), "motivo": "fila_clientes_sin_duenio"})
            continue
        sin_titulos = _quitar_titulos(nombre_duenio)
        partes = sin_titulos.split()
        if len(partes) == 1 and partes[0]:
            reporte["sin_apellido"]["duenios"].append({"hoja": "Clientes_y_Mascotas", "fila": f["fila_excel"], "nombre": nombre_duenio})
            hallazgos_csv.append({"hoja": "Clientes_y_Mascotas", "fila": str(f["fila_excel"]), "motivo": f"duenio_sin_apellido:{nombre_duenio}"})
    # contar personas distintas por nombre normalizado
    duenios_distintos = {}
    for item in reporte["sin_apellido"]["duenios"]:
        key = _normalizar_minimo(item["nombre"])
        if key not in duenios_distintos:
            duenios_distintos[key] = item
    reporte["sin_apellido"]["duenios"] = list(duenios_distintos.values())

    for f in atenciones:
        vet = str(f["valores"]["Veterinario_Tratante"]["texto"]).strip()
        if vet:
            sin_titulos = _quitar_titulos(vet)
            partes = sin_titulos.split()
            if len(partes) == 1 and partes[0]:
                reporte["sin_apellido"]["veterinarios"].append({"hoja": "Atenciones_Clinicas", "fila": f["fila_excel"], "nombre": vet})
                hallazgos_csv.append({"hoja": "Atenciones_Clinicas", "fila": str(f["fila_excel"]), "motivo": f"veterinario_sin_apellido:{vet}"})
    vet_distintos = {}
    for item in reporte["sin_apellido"]["veterinarios"]:
        key = _normalizar_minimo(item["nombre"])
        if key not in vet_distintos:
            vet_distintos[key] = item
    reporte["sin_apellido"]["veterinarios"] = list(vet_distintos.values())

    # Construir padrón (Clientes_y_Mascotas) - titular normalizado + nombre mascota normalizado
    padron_claves = set()
    for f in clientes:
        if f["totalmente_vacia"]:
            continue
        duenio = _normalizar_minimo(f["valores"]["Nombre_Duenio"]["texto"])
        mascota = _normalizar_minimo(f["valores"]["Nombre_Mascota"]["texto"])
        if duenio and mascota:
            padron_claves.add((duenio, mascota))
        elif mascota:
            padron_claves.add(("", mascota))
    padron_por_mascota = set()
    for f in clientes:
        if f["totalmente_vacia"]:
            continue
        mascota = _normalizar_minimo(f["valores"]["Nombre_Mascota"]["texto"])
        if mascota:
            padron_por_mascota.add(mascota)

    # Mascotas huérfanas en atenciones y guardería - contar animales distintos (titular+mascota normalizados)
    huerfanas_dict: dict[tuple[str, str], dict[str, Any]] = {}
    for f in atenciones:
        mascota_norm = _normalizar_minimo(f["valores"]["Paciente_Mascota"]["texto"])
        duenio_ref_norm = _normalizar_minimo(f["valores"]["Duenio_Referencia"]["texto"])
        if not mascota_norm:
            continue
        coincide = (duenio_ref_norm, mascota_norm) in padron_claves or mascota_norm in padron_por_mascota
        if not coincide:
            key_at = (duenio_ref_norm, mascota_norm)
            if key_at not in huerfanas_dict:
                huerfanas_dict[key_at] = {"hoja": "Atenciones_Clinicas", "fila": f["fila_excel"], "mascota": f["valores"]["Paciente_Mascota"]["texto"], "tutor": duenio_ref_norm}
            hallazgos_csv.append({"hoja": "Atenciones_Clinicas", "fila": str(f["fila_excel"]), "motivo": "mascota_sin_duenio"})
    for f in guarderia:
        mascota_norm = _normalizar_minimo(f["valores"]["Mascota"]["texto"])
        tutor_norm = _normalizar_minimo(f["valores"]["Tutor"]["texto"])
        if not mascota_norm:
            continue
        coincide = (tutor_norm, mascota_norm) in padron_claves or mascota_norm in padron_por_mascota
        if not coincide:
            key_g = (tutor_norm, mascota_norm)
            if key_g not in huerfanas_dict:
                huerfanas_dict[key_g] = {"hoja": "Guarderia_y_Estadias", "fila": f["fila_excel"], "mascota": f["valores"]["Mascota"]["texto"], "tutor": tutor_norm}
            hallazgos_csv.append({"hoja": "Guarderia_y_Estadias", "fila": str(f["fila_excel"]), "motivo": "mascota_sin_duenio"})
    reporte["huerfanas_en_otras_hojas"] = list(huerfanas_dict.values())
    reporte["mascotas_sin_duenio"] = list(huerfanas_dict.values())

    # Duplicados
    personas_list = []
    for f in clientes:
        if f["totalmente_vacia"]:
            continue
        duenio = str(f["valores"]["Nombre_Duenio"]["texto"]).strip()
        if not duenio:
            continue
        tel_info = f["valores"]["Telefono_Contacto"]
        tel_num, _tel_flags = _normalizar_telefono_minimo(str(tel_info["texto"]))
        personas_list.append({
            "hoja": "Clientes_y_Mascotas",
            "fila": f["fila_excel"],
            "nombre": duenio,
            "nombre_norm": _normalizar_minimo(duenio),
            "tel_num": tel_num,
            "tel_orig": tel_info["texto"],
        })
    por_nombre_tel_dict: dict[str, list[dict[str, Any]]] = {}
    for p in personas_list:
        k = str((str(p["nombre_norm"]), str(p["tel_num"])))
        por_nombre_tel_dict.setdefault(k, []).append(p)
    for key, items in por_nombre_tel_dict.items():
        if len(items) >= 2:
            # check if same tel
            tels_k = set(str(x["tel_num"]) for x in items)
            noms_k = set(str(x["nombre_norm"]) for x in items)
            if len(tels_k) == 1 and len(noms_k) == 1 and list(tels_k)[0]:
                reporte["duplicados"]["misma_persona"].append(items)
    por_nombre: dict[str, list[dict[str, Any]]] = {}
    for p in personas_list:
        if p["nombre_norm"]:
            por_nombre.setdefault(str(p["nombre_norm"]), []).append(p)
    for nombre_n, items in por_nombre.items():
        if len(items) >= 2:
            tels_set = set(str(x["tel_num"]) for x in items if x["tel_num"])
            if len(tels_set) >= 2:
                reporte["duplicados"]["revisar"].append(items)
    por_tel: dict[str, list[dict[str, Any]]] = {}
    for p in personas_list:
        if p["tel_num"]:
            por_tel.setdefault(str(p["tel_num"]), []).append(p)
    for tel_n, items in por_tel.items():
        if len(items) >= 2:
            nombres = set(str(x["nombre_norm"]) for x in items if x["nombre_norm"])
            if len(nombres) >= 2:
                reporte["duplicados"]["familia"].append(items)

    # Deuda en el texto (solo indicio)
    for hnombre, hdata in hojas.items():
        for f in hdata["filas"]:
            textos = [str(v.get("texto", "")) for v in f["valores"].values()]
            if _tiene_deuda_en_texto(*textos):
                reporte["deuda_en_el_texto"].append({"hoja": hnombre, "fila": f["fila_excel"]})
                hallazgos_csv.append({"hoja": hnombre, "fila": str(f["fila_excel"]), "motivo": "deuda_en_el_texto_indicio"})

    # Guardar JSON (sin hora de generación)
    json_path = salida_dir / "perfilado.json"
    csv_path = salida_dir / "perfilado_filas.csv"

    # Asegurar que no hay timestamp
    reporte_serializable = json.loads(json.dumps(reporte, default=str))

    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(reporte_serializable, fh, ensure_ascii=False, indent=2, sort_keys=False)

    with open(csv_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["hoja", "fila", "motivo"])
        writer.writeheader()
        for h in hallazgos_csv:
            writer.writerow(h)

    # Resumen por consola
    print("=== PERFILADO MIGRACIÓN (solo lectura) ===")
    print(f"Fecha última edición libro: {reporte['fecha_ultima_edicion']}")
    if reporte.get("advertencia_fecha"):
        print(f"ADVERTENCIA: {reporte['advertencia_fecha']}")
    print(f"Filas por hoja: {reporte['conteo_filas_por_hoja']}")
    print(f"Duplicados probables (misma_persona + revisar): {len(reporte['duplicados']['misma_persona']) + len(reporte['duplicados']['revisar'])}")
    print(f"Familia (informativo): {len(reporte['duplicados']['familia'])}")
    print(f"Mascotas sin dueño/huérfanas: {len(reporte['mascotas_sin_duenio'])}")
    print(f"Filas totalmente vacías: {len(reporte['filas_totalmente_vacias'])}")
    print(f"Sin DNI - columna inexistente: {reporte['dni']['columna_inexistente']}, sin_dni: {reporte['dni']['sin_dni']}")
    print(f"Sin apellido - dueños: {len(reporte['sin_apellido']['duenios'])}, veterinarios: {len(reporte['sin_apellido']['veterinarios'])}")
    print(f"Reporte JSON: {json_path}")
    print(f"Reporte CSV: {csv_path}")
    print("==========================================")

    return reporte
