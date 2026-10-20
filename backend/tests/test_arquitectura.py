"""Regla de arquitectura: un módulo no puede importar models/repository de otro módulo, y core no puede importar módulos."""

import ast
from dataclasses import dataclass
from pathlib import Path

MODULOS = frozenset(
    {"identidad", "padron", "migracion", "cobros", "panel", "guarderia", "clinica"}
)
SUBPAQUETES_PROHIBIDOS = frozenset({"models", "repository", "repositories"})


@dataclass(frozen=True)
class Violacion:
    archivo: str
    importado: str
    detalle: str


def _modulo_actual(relativo: Path) -> str:
    """Módulo al que pertenece un archivo, relativo a la raíz de la app."""
    partes = relativo.parts
    if partes[0] == "modules" and len(partes) > 2:
        return partes[1]
    return partes[0]


def _imports_del_archivo(arbol: ast.AST, paquete: tuple[str, ...]) -> list[str]:
    """Cadenas de módulo importadas (las relativas quedan resueltas a absolutas)."""
    importados: list[str] = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            for alias in nodo.names:
                importados.append(alias.name)
        elif isinstance(nodo, ast.ImportFrom):
            if nodo.level > len(paquete) + 1:
                continue
            base = paquete[: len(paquete) - (nodo.level - 1)] if nodo.level else ()
            cadena = ".".join(
                trozo for trozo in (".".join(base), nodo.module or "") if trozo
            )
            if cadena:
                importados.append(cadena)
            for alias in nodo.names:
                importados.append(
                    ".".join(trozo for trozo in (cadena, alias.name) if trozo)
                )
    return importados


def _cadena_restringida(cadena: str) -> str | None:
    """Devuelve la parte prohibida de la cadena (ej. 'padron.models') o None."""
    partes = cadena.split(".")
    for indice, parte in enumerate(partes[1:], start=1):
        if parte in SUBPAQUETES_PROHIBIDOS:
            return ".".join(partes[: indice + 1])
    return None


def encontrar_violaciones(ruta: str | Path) -> list[Violacion]:
    """Recorre los .py bajo ``ruta`` (la carpeta app/) y lista violaciones de arquitectura.

    (a) un módulo importa models/repository/repositories de OTRO módulo;
    (b) core importa cualquier módulo.
    Importar service o schemas de otro módulo está permitido.
    Los archivos sueltos directamente en app/ (ej. main.py) quedan exentos de la regla
    de módulos. Solo aplica a archivos bajo app/modules/ o a los propios módulos
    detectados; app/core sigue sin poder importar ningún módulo.
    """
    raiz = Path(ruta)
    violaciones: dict[tuple[str, str], Violacion] = {}

    for archivo in sorted(raiz.rglob("*.py")):
        relativo = archivo.relative_to(raiz)
        # Exención: archivos sueltos directamente en backend/app/ quedan exentos de la
        # regla de módulos (solo se aplica a app/modules/<nombre>/...).
        if len(relativo.parts) == 1:
            continue
        actual = _modulo_actual(relativo)
        arbol = ast.parse(archivo.read_text(encoding="utf-8-sig"), filename=str(archivo))
        paquete = relativo.parent.parts

        for cadena in _imports_del_archivo(arbol, paquete):
            partes = cadena.split(".")
            objetivos = [parte for parte in partes if parte in MODULOS]
            if not objetivos:
                continue
            objetivo = objetivos[0]
            if objetivo == actual:
                continue

            if actual == "core":
                violacion = Violacion(
                    archivo=str(relativo),
                    importado=cadena,
                    detalle=f"core importa el módulo '{objetivo}'",
                )
            else:
                restringida = _cadena_restringida(cadena)
                if restringida is None:
                    continue
                violacion = Violacion(
                    archivo=str(relativo),
                    importado=restringida,
                    detalle=(
                        f"el módulo '{actual}' importa '{restringida}' "
                        f"de otro módulo ('{objetivo}')"
                    ),
                )

            clave = (str(relativo), violacion.importado)
            prefijo_ya_registrado = any(
                clave[0] == archivo_registrado
                and clave[1].startswith(f"{importado_registrado}.")
                for archivo_registrado, importado_registrado in violaciones
            )
            if clave not in violaciones and not prefijo_ya_registrado:
                violaciones[clave] = violacion

    return list(violaciones.values())


def _escribir(ruta: Path, contenido: str = "") -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(contenido, encoding="utf-8")


def test_importar_models_de_otro_modulo_es_violacion(tmp_path: Path) -> None:
    _escribir(tmp_path / "padron" / "models.py")
    _escribir(
        tmp_path / "identidad" / "api.py",
        "from padron import models\nimport padron.models\n",
    )

    violaciones = encontrar_violaciones(tmp_path)

    assert [v.importado for v in violaciones] == ["padron.models"]
    assert violaciones[0].archivo == str(Path("identidad") / "api.py")


def test_importar_repository_de_otro_modulo_es_violacion(tmp_path: Path) -> None:
    _escribir(
        tmp_path / "clinica" / "api.py",
        "from guarderia.repository import ReservaRepo\n",
    )

    violaciones = encontrar_violaciones(tmp_path)

    assert [v.importado for v in violaciones] == ["guarderia.repository"]


def test_importar_service_o_schemas_de_otro_modulo_es_permitido(tmp_path: Path) -> None:
    _escribir(tmp_path / "padron" / "service.py")
    _escribir(tmp_path / "padron" / "schemas.py")
    _escribir(
        tmp_path / "identidad" / "api.py",
        "from padron import service\nfrom padron.schemas import MascotaOut\n",
    )

    assert encontrar_violaciones(tmp_path) == []


def test_import_relativo_de_models_es_violacion(tmp_path: Path) -> None:
    _escribir(
        tmp_path / "identidad" / "api.py",
        "from ..padron.models import Mascota\n",
    )

    violaciones = encontrar_violaciones(tmp_path)

    assert [v.importado for v in violaciones] == ["padron.models"]


def test_import_relativo_de_service_es_permitido(tmp_path: Path) -> None:
    _escribir(
        tmp_path / "identidad" / "api.py",
        "from ..padron.service import buscar_mascota\n",
    )

    assert encontrar_violaciones(tmp_path) == []


def test_importar_repositories_de_otro_modulo_es_violacion(tmp_path: Path) -> None:
    _escribir(
        tmp_path / "cobros" / "api.py",
        "from padron.repositories import PersonaRepo\n",
    )

    violaciones = encontrar_violaciones(tmp_path)

    assert [v.importado for v in violaciones] == ["padron.repositories"]


def test_archivo_suelto_directamente_en_app_exento(tmp_path: Path) -> None:
    # Los archivos sueltos directamente en app/ (como main.py) quedan exentos de
    # la regla de módulos.
    _escribir(
        tmp_path / "main.py",
        "from padron import models\n",
    )

    assert encontrar_violaciones(tmp_path) == []


def test_archivo_con_bom_no_rompe_y_detecta_violacion(tmp_path: Path) -> None:
    # El archivo se escribe con bytes BOM UTF-8 al comienzo; debe leerse con
    # encoding="utf-8-sig" sin romper y seguir detectando violaciones.
    ruta = tmp_path / "identidad" / "api.py"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    contenido = "from padron import models\n"
    ruta.write_bytes(b"\xef\xbb\xbf" + contenido.encode("utf-8"))

    violaciones = encontrar_violaciones(tmp_path)

    assert [v.importado for v in violaciones] == ["padron.models"]


def test_imports_reales_y_relativos_entre_modulos_y_permitidos(tmp_path: Path) -> None:
    # Estructura real: app/modules/<nombre>/
    app_raiz = tmp_path / "app"
    modulos = app_raiz / "modules"
    _escribir(modulos / "padron" / "models.py")
    _escribir(modulos / "padron" / "service.py")
    _escribir(modulos / "padron" / "schemas.py")
    _escribir(modulos / "cobros" / "api.py")
    _escribir(modulos / "cobros" / "service.py")

    # Imports reales desde app.modules.cobros - casos permitidos
    ruta_cobros = modulos / "cobros" / "api.py"
    ruta_cobros.write_text(
        # service y schemas de otro módulo permitidos
        "from app.modules.padron import service\n"
        "from app.modules.padron.schemas import CargoOut\n"
        # el propio módulo consigo mismo permitido
        "from app.modules.cobros import service\n",
        encoding="utf-8",
    )

    violaciones = encontrar_violaciones(app_raiz)
    assert violaciones == []

    # Imports reales de models desde otro módulo - violaciones (ambas formas se detectan)
    ruta_cobros_models = modulos / "cobros" / "api_models.py"
    ruta_cobros_models.write_text(
        "from app.modules.padron import models\n"
        "import app.modules.padron.models\n",
        encoding="utf-8",
    )
    violaciones_models = encontrar_violaciones(app_raiz)
    assert len(violaciones_models) == 1
    ruta_cobros_models.unlink()

    # Imports relativos reales
    ruta_cobros_rel = modulos / "cobros" / "api_rel.py"
    ruta_cobros_rel.write_text(
        "from ..padron import models\n"
        "from ..padron.models import X\n",
        encoding="utf-8",
    )

    violaciones_rel = encontrar_violaciones(app_raiz)
    assert len(violaciones_rel) == 1


def test_core_importando_cualquier_modulo_es_violacion(tmp_path: Path) -> None:
    _escribir(
        tmp_path / "core" / "config.py",
        "from identidad import service\nimport padron\n",
    )

    violaciones = encontrar_violaciones(tmp_path)

    assert sorted(v.importado for v in violaciones) == ["identidad", "padron"]


def test_app_real_cero_violaciones() -> None:
    raiz_app = Path(__file__).resolve().parents[1] / "app"

    assert encontrar_violaciones(raiz_app) == []
