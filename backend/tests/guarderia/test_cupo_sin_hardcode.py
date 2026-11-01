import ast
from pathlib import Path


def test_cupo_no_tiene_enteros_de_negocio_hardcodeados() -> None:
    ruta = (
        Path(__file__).resolve().parents[2]
        / "app"
        / "modules"
        / "guarderia"
        / "cupo.py"
    )
    arbol = ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))
    enteros = [
        nodo.value
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.Constant)
        and type(nodo.value) is int
        and nodo.value not in {0, 1}
    ]

    assert enteros == []
