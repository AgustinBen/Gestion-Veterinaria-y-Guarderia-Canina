from sqlalchemy import inspect


def test_tablas_clinicas_no_tienen_columnas_de_dinero_y_solo_vinculan_cargo(
    engine_sqlite,
) -> None:
    inspector = inspect(engine_sqlite)
    columnas = {
        tabla: {columna["name"] for columna in inspector.get_columns(tabla)}
        for tabla in ("atencion", "vacuna_aplicada")
    }
    nombres_prohibidos = {
        "monto",
        "costo",
        "precio",
        "total",
        "saldo",
        "pago",
    }
    assert all(
        nombre not in nombres_prohibidos
        for nombres in columnas.values()
        for nombre in nombres
    )
    assert columnas["atencion"] & {
        "monto",
        "costo",
        "precio",
        "total",
        "saldo",
        "pago",
    } == set()
    assert "cargo_id" in columnas["atencion"]
    claves_cobros = [
        clave
        for clave in inspector.get_foreign_keys("atencion")
        if clave["referred_table"] == "cargo"
    ]
    assert len(claves_cobros) == 1
    assert claves_cobros[0]["constrained_columns"] == ["cargo_id"]
