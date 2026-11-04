from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.parametros import get_param
from app.modules.guarderia import service
from app.modules.guarderia.franjas import Franja
from app.modules.guarderia.models import Ocupacion
from app.modules.identidad.permisos import Rol

RUTA_CONFIGURACION = "/api/guarderia/configuracion/cupo"


def test_solo_duenio_lee_y_actualiza_configuracion(
    client: TestClient,
    db_session: Session,
    sembrar_cupo,
    crear_usuario,
    token_guarderia,
) -> None:
    duenio = crear_usuario(Rol.DUENIO)
    personal = crear_usuario(Rol.PERSONAL)
    veterinario = crear_usuario(Rol.VETERINARIO)

    assert client.get(RUTA_CONFIGURACION).status_code == 401
    minimo = get_param(db_session, "guarderia.cupo_minimo")
    assert (
        client.put(RUTA_CONFIGURACION, json={"cupo_maximo": minimo}).status_code
        == 401
    )

    for usuario in (personal, veterinario):
        headers = token_guarderia(usuario)
        assert client.get(RUTA_CONFIGURACION, headers=headers).status_code == 403
        assert (
            client.put(
                RUTA_CONFIGURACION,
                json={"cupo_maximo": minimo},
                headers=headers,
            ).status_code
            == 403
        )

    headers = token_guarderia(duenio)
    configuracion = client.get(RUTA_CONFIGURACION, headers=headers)
    assert configuracion.status_code == 200
    assert (
        client.put(
            RUTA_CONFIGURACION,
            json={"cupo_maximo": configuracion.json()["cupo_maximo"]},
            headers=headers,
        ).status_code
        == 200
    )


def test_cupo_respeta_limites_configurables_y_persisten(
    client: TestClient,
    db_session: Session,
    sembrar_cupo,
    crear_usuario,
    token_guarderia,
) -> None:
    usuario = crear_usuario(Rol.DUENIO)
    headers = token_guarderia(usuario)
    minimo = get_param(db_session, "guarderia.cupo_minimo")
    maximo_permitido = get_param(db_session, "guarderia.cupo_maximo_permitido")

    dentro_limite = client.put(
        RUTA_CONFIGURACION,
        json={"cupo_maximo": minimo},
        headers=headers,
    )
    assert dentro_limite.status_code == 200
    assert dentro_limite.json()["cupo_maximo"] == minimo
    assert get_param(db_session, "guarderia.cupo_maximo") == minimo

    for valor in (minimo - 1, maximo_permitido + 1):
        respuesta = client.put(
            RUTA_CONFIGURACION,
            json={"cupo_maximo": valor},
            headers=headers,
        )
        assert respuesta.status_code == 422

    decimal = client.put(
        RUTA_CONFIGURACION,
        json={"cupo_maximo": f"{minimo}.5"},
        headers=headers,
    )
    assert decimal.status_code == 422
    assert get_param(db_session, "guarderia.cupo_maximo") == minimo


def test_configuracion_generica_tambien_valida_los_limites_de_cupo(
    client: TestClient,
    db_session: Session,
    sembrar_cupo,
    crear_usuario,
    token_guarderia,
) -> None:
    usuario = crear_usuario(Rol.DUENIO)
    headers = token_guarderia(usuario)
    minimo = get_param(db_session, "guarderia.cupo_minimo")

    invalido = client.put(
        "/api/config/guarderia.cupo_maximo",
        json={"valor": minimo - 1},
        headers=headers,
    )
    assert invalido.status_code == 422

    valido = client.put(
        "/api/config/guarderia.cupo_maximo",
        json={"valor": minimo},
        headers=headers,
    )
    assert valido.status_code == 200
    assert get_param(db_session, "guarderia.cupo_maximo") == minimo


def test_bajar_cupo_muestra_cero_y_exceso_sin_cancelar_reservas(
    client: TestClient,
    db_session: Session,
    sembrar_cupo,
    crear_usuario,
    token_guarderia,
    crear_pacientes,
    crear_ocupaciones,
) -> None:
    usuario = crear_usuario(Rol.DUENIO)
    headers = token_guarderia(usuario)
    minimo = get_param(db_session, "guarderia.cupo_minimo")
    plazas_emergencia = get_param(db_session, "guarderia.plazas_emergencia")
    fecha = date.today() + timedelta(days=1)
    pacientes = crear_pacientes([("Perro", None)] * (minimo + 1))
    crear_ocupaciones(pacientes, fecha, Franja.DIA, usuario.id)

    respuesta = client.put(
        RUTA_CONFIGURACION,
        json={"cupo_maximo": minimo},
        headers=headers,
    )

    assert respuesta.status_code == 200
    config = respuesta.json()
    assert config["cupo_maximo"] == minimo
    assert config["sobreocupaciones"] == [
        {
            "fecha": fecha.isoformat(),
            "franja": "DIA",
            "publico": minimo - plazas_emergencia,
            "ocupado": minimo + 1,
            "exceso": minimo + 1 - (minimo - plazas_emergencia),
        }
    ]

    cantidad_ocupaciones = db_session.execute(
        select(func.count(Ocupacion.id))
    ).scalar_one()
    assert cantidad_ocupaciones == minimo + 1

    disponibilidad = client.get(
        "/api/guarderia/disponibilidad",
        params={"fecha": fecha.isoformat(), "franja": Franja.DIA.value},
        headers=headers,
    )
    assert disponibilidad.status_code == 200
    assert disponibilidad.json()["disponible"] == 0
    assert disponibilidad.json()["exceso_ocupacion"] == (
        minimo + 1 - (minimo - plazas_emergencia)
    )


def test_excepcion_por_fecha_persiste_y_se_usa_en_disponibilidad_y_reservas(
    client: TestClient,
    db_session: Session,
    sembrar_cupo,
    crear_usuario,
    token_guarderia,
    crear_pacientes,
    crear_ocupaciones,
) -> None:
    usuario = crear_usuario(Rol.DUENIO)
    headers = token_guarderia(usuario)
    minimo = get_param(db_session, "guarderia.cupo_minimo")
    maximo_permitido = get_param(db_session, "guarderia.cupo_maximo_permitido")
    plazas_emergencia = get_param(db_session, "guarderia.plazas_emergencia")
    fecha = date.today() + timedelta(days=1)
    fecha_sin_excepcion = fecha + timedelta(days=1)

    excepcion = client.put(
        RUTA_CONFIGURACION,
        json={"cupo_maximo": minimo, "fecha": fecha.isoformat()},
        headers=headers,
    )
    assert excepcion.status_code == 200
    assert excepcion.json()["cupo_fecha"] == minimo
    assert excepcion.json()["fecha_es_excepcion"] is True

    global_actualizado = client.put(
        RUTA_CONFIGURACION,
        json={"cupo_maximo": maximo_permitido},
        headers=headers,
    )
    assert global_actualizado.status_code == 200

    configuracion_fecha = client.get(
        RUTA_CONFIGURACION,
        params={"fecha": fecha.isoformat()},
        headers=headers,
    )
    assert configuracion_fecha.status_code == 200
    assert configuracion_fecha.json()["cupo_maximo"] == maximo_permitido
    assert configuracion_fecha.json()["cupo_fecha"] == minimo
    assert configuracion_fecha.json()["fecha_es_excepcion"] is True

    filas = client.get(
        "/api/guarderia/calendario",
        params={"desde": fecha.isoformat(), "hasta": fecha_sin_excepcion.isoformat()},
        headers=headers,
    )
    assert filas.status_code == 200
    assert {
        fila["cupo_maximo"]
        for fila in filas.json()
        if fila["fecha"] == fecha.isoformat()
    } == {minimo}
    assert {
        fila["cupo_maximo"]
        for fila in filas.json()
        if fila["fecha"] == fecha_sin_excepcion.isoformat()
    } == {maximo_permitido}

    cupo_publico = minimo - plazas_emergencia
    ocupados = crear_pacientes([("Perro", None)] * cupo_publico)
    nuevo = crear_pacientes([("Perro", None)])
    if ocupados:
        crear_ocupaciones(ocupados, fecha, Franja.DIA, usuario.id)

    resultado = service.verificar_cupo(
        db_session,
        nuevo,
        (fecha, Franja.DIA),
        (fecha, Franja.DIA),
    )
    assert resultado.aprobado is False
    assert resultado.codigo == "SIN_CUPO"
