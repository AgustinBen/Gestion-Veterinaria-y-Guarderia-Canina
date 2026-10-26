"""Tests de la configuración parametrizable gestionada por el Dueño."""

from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import parametros
from app.core.models import Configuracion
from app.modules.identidad.permisos import Rol


def _contar_config(db: Session) -> int:
    return db.execute(select(func.count()).select_from(Configuracion)).scalar_one()


def _config(db: Session, clave: str) -> Configuracion | None:
    db.expire_all()
    stmt = select(Configuracion).where(Configuracion.clave == clave)
    return db.execute(stmt).scalar_one_or_none()


def test_get_config_solo_duenio(
    client, duenio, crear_usuario, auth_de, sembrar_config
) -> None:
    sembrar_config("zeta", 5, "int")
    sembrar_config("alfa", "hola", "str")
    personal = crear_usuario("personal", rol=Rol.PERSONAL)
    veterinario = crear_usuario("veterinario", rol=Rol.VETERINARIO)

    respuesta = client.get("/api/config", headers=auth_de(duenio))

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert [parametro["clave"] for parametro in datos] == ["alfa", "zeta"]
    assert datos[0]["valor"] == "hola"
    assert datos[0]["tipo"] == "str"
    assert datos[0]["updated_by"] is None
    assert datos[0]["updated_at"] is not None
    assert datos[1]["valor"] == "5"
    assert datos[1]["tipo"] == "int"

    assert (
        client.get("/api/config", headers=auth_de(personal)).status_code == 403
    )
    assert (
        client.get("/api/config", headers=auth_de(veterinario)).status_code == 403
    )
    assert client.get("/api/config").status_code == 401


def test_put_int_acepta_int_y_string(
    client, duenio, auth_de, sembrar_config, db_session: Session
) -> None:
    sembrar_config("cupo", 10, "int")
    headers = auth_de(duenio)

    primero = client.put("/api/config/cupo", headers=headers, json={"valor": 20})
    segundo = client.put(
        "/api/config/cupo", headers=headers, json={"valor": " 30 "}
    )

    assert primero.status_code == 200
    assert primero.json()["valor"] == "20"
    assert primero.json()["tipo"] == "int"
    assert primero.json()["updated_by"] == "duenio"
    assert segundo.status_code == 200
    assert segundo.json()["valor"] == "30"
    assert parametros.get_param(db_session, "cupo") == 30

    guardado = _config(db_session, "cupo")
    assert guardado is not None
    assert guardado.tipo == "int"
    assert guardado.valor == "30"
    assert guardado.updated_by == "duenio"


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [(2, "2"), (2.5, "2.5"), ("3.125", "3.125")],
)
def test_put_decimal_acepta_int_float_y_string(
    client,
    duenio,
    auth_de,
    sembrar_config,
    db_session: Session,
    valor: object,
    esperado: str,
) -> None:
    sembrar_config("precio", Decimal("1.00"), "decimal")

    respuesta = client.put(
        "/api/config/precio",
        headers=auth_de(duenio),
        json={"valor": valor},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["valor"] == esperado
    assert respuesta.json()["tipo"] == "decimal"
    assert parametros.get_param(db_session, "precio") == Decimal(esperado)


@pytest.mark.parametrize("valor", ["abc", "", "NaN", "Infinity", "-Infinity"])
def test_put_decimal_rechaza_valores_invalidos(
    client,
    duenio,
    auth_de,
    sembrar_config,
    db_session: Session,
    valor: str,
) -> None:
    sembrar_config("precio", Decimal("1.50"), "decimal")

    respuesta = client.put(
        "/api/config/precio",
        headers=auth_de(duenio),
        json={"valor": valor},
    )

    assert respuesta.status_code == 422
    guardado = _config(db_session, "precio")
    assert guardado is not None
    assert guardado.valor == "1.50"


def test_put_bool_acepta_bool_y_string(
    client, duenio, auth_de, sembrar_config, db_session: Session
) -> None:
    sembrar_config("activo", False, "bool")
    headers = auth_de(duenio)

    primero = client.put(
        "/api/config/activo", headers=headers, json={"valor": True}
    )
    segundo = client.put(
        "/api/config/activo", headers=headers, json={"valor": "false"}
    )

    assert primero.status_code == 200
    assert primero.json()["valor"] == "true"
    assert segundo.status_code == 200
    assert segundo.json()["valor"] == "false"
    assert parametros.get_param(db_session, "activo") is False


@pytest.mark.parametrize("valor", [1, 0, "1", "0", "yes", "", None])
def test_put_bool_rechaza_valores_invalidos(
    client,
    duenio,
    auth_de,
    sembrar_config,
    db_session: Session,
    valor: object,
) -> None:
    sembrar_config("activo", True, "bool")

    respuesta = client.put(
        "/api/config/activo",
        headers=auth_de(duenio),
        json={"valor": valor},
    )

    assert respuesta.status_code == 422
    guardado = _config(db_session, "activo")
    assert guardado is not None
    assert guardado.valor == "true"


def test_put_str_acepta_solo_string(
    client, duenio, auth_de, sembrar_config, db_session: Session
) -> None:
    sembrar_config("nombre", "hola", "str")

    respuesta = client.put(
        "/api/config/nombre",
        headers=auth_de(duenio),
        json={"valor": "mundo"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["valor"] == "mundo"
    assert parametros.get_param(db_session, "nombre") == "mundo"


@pytest.mark.parametrize("valor", [123, 1.5, True, None])
def test_put_str_rechaza_no_string(
    client,
    duenio,
    auth_de,
    sembrar_config,
    db_session: Session,
    valor: object,
) -> None:
    sembrar_config("nombre", "hola", "str")

    respuesta = client.put(
        "/api/config/nombre",
        headers=auth_de(duenio),
        json={"valor": valor},
    )

    assert respuesta.status_code == 422
    guardado = _config(db_session, "nombre")
    assert guardado is not None
    assert guardado.valor == "hola"


def test_put_clave_inexistente_404_y_no_crea(
    client, duenio, auth_de, db_session: Session
) -> None:
    antes = _contar_config(db_session)

    respuesta = client.put(
        "/api/config/no_existe",
        headers=auth_de(duenio),
        json={"valor": "x"},
    )

    assert respuesta.status_code == 404
    assert respuesta.json() == {"detail": "Configuración no encontrada"}
    assert _contar_config(db_session) == antes
    assert _config(db_session, "no_existe") is None


def test_put_no_permite_cambiar_tipo(
    client, duenio, auth_de, sembrar_config, db_session: Session
) -> None:
    sembrar_config("cupo", 10, "int")

    respuesta = client.put(
        "/api/config/cupo",
        headers=auth_de(duenio),
        json={"valor": 20, "tipo": "str"},
    )

    assert respuesta.status_code == 422
    guardado = _config(db_session, "cupo")
    assert guardado is not None
    assert guardado.tipo == "int"
    assert guardado.valor == "10"


def test_put_valor_null_422(
    client, duenio, auth_de, sembrar_config, db_session: Session
) -> None:
    sembrar_config("cupo", 10, "int")

    respuesta = client.put(
        "/api/config/cupo",
        headers=auth_de(duenio),
        json={"valor": None},
    )

    assert respuesta.status_code == 422
    guardado = _config(db_session, "cupo")
    assert guardado is not None
    assert guardado.valor == "10"


@pytest.mark.parametrize("rol", [Rol.PERSONAL, Rol.VETERINARIO])
def test_put_no_duenio_403(
    client,
    crear_usuario,
    auth_de,
    sembrar_config,
    db_session: Session,
    rol: Rol,
) -> None:
    usuario = crear_usuario(f"user_{rol.value}", rol=rol)
    sembrar_config("cupo", 1, "int")

    respuesta = client.put(
        "/api/config/cupo",
        headers=auth_de(usuario),
        json={"valor": 2},
    )

    assert respuesta.status_code == 403
    guardado = _config(db_session, "cupo")
    assert guardado is not None
    assert guardado.valor == "1"


def test_put_sin_token_401(client, sembrar_config) -> None:
    sembrar_config("cupo", 1, "int")

    respuesta = client.put("/api/config/cupo", json={"valor": 2})

    assert respuesta.status_code == 401
