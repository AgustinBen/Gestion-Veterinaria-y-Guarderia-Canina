from datetime import date, timedelta

import pytest

from app.modules.guarderia.franjas import Franja
from app.modules.identidad.permisos import Rol

RUTA_DISPONIBILIDAD = "/api/guarderia/disponibilidad"
RUTA_CALENDARIO = "/api/guarderia/calendario"
RUTA_EMERGENCIA = "/api/guarderia/emergencias"
FECHA = date(2030, 12, 15)


@pytest.mark.parametrize("rol", list(Rol))
@pytest.mark.parametrize(
    ("ruta", "parametros"),
    [
        (
            RUTA_DISPONIBILIDAD,
            {"fecha": FECHA.isoformat(), "franja": Franja.DIA.value},
        ),
        (
            RUTA_CALENDARIO,
            {"desde": FECHA.isoformat(), "hasta": FECHA.isoformat()},
        ),
    ],
)
def test_endpoints_son_de_lectura_para_los_tres_roles(
    client,
    sembrar_cupo,
    crear_usuario,
    token_guarderia,
    rol: Rol,
    ruta: str,
    parametros: dict[str, str],
) -> None:
    usuario = crear_usuario(rol)

    respuesta = client.get(
        ruta,
        params=parametros,
        headers=token_guarderia(usuario),
    )

    assert respuesta.status_code == 200


@pytest.mark.parametrize(
    ("ruta", "parametros"),
    [
        (
            RUTA_DISPONIBILIDAD,
            {"fecha": FECHA.isoformat(), "franja": Franja.DIA.value},
        ),
        (
            RUTA_CALENDARIO,
            {"desde": FECHA.isoformat(), "hasta": FECHA.isoformat()},
        ),
    ],
)
def test_endpoints_requieren_autenticacion(
    client,
    sembrar_cupo,
    ruta: str,
    parametros: dict[str, str],
) -> None:
    respuesta = client.get(ruta, params=parametros)

    assert respuesta.status_code == 401


def test_calendario_rechaza_rango_mayor_al_limite_tecnico(
    client,
    sembrar_cupo,
    crear_usuario,
    token_guarderia,
) -> None:
    usuario = crear_usuario(Rol.DUENIO)
    desde = date(2030, 1, 1)
    hasta = desde + timedelta(days=366)

    respuesta = client.get(
        RUTA_CALENDARIO,
        params={"desde": desde.isoformat(), "hasta": hasta.isoformat()},
        headers=token_guarderia(usuario),
    )

    assert respuesta.status_code == 422


def test_calendario_devuelve_una_fila_por_fecha_y_franja(
    client,
    sembrar_cupo,
    crear_usuario,
    token_guarderia,
) -> None:
    usuario = crear_usuario(Rol.DUENIO)
    desde = date(2030, 12, 15)
    hasta = desde + timedelta(days=1)

    respuesta = client.get(
        RUTA_CALENDARIO,
        params={"desde": desde.isoformat(), "hasta": hasta.isoformat()},
        headers=token_guarderia(usuario),
    )

    assert respuesta.status_code == 200
    filas = respuesta.json()
    assert len(filas) == 4
    assert [(fila["fecha"], fila["franja"]) for fila in filas] == [
        ("2030-12-15", "DIA"),
        ("2030-12-15", "NOCHE"),
        ("2030-12-16", "DIA"),
        ("2030-12-16", "NOCHE"),
    ]


def test_dueño_habilita_plaza_de_emergencia_con_idempotencia(
    client,
    db_session,
    sembrar_cupo,
    crear_usuario,
    token_guarderia,
) -> None:
    usuario = crear_usuario(Rol.DUENIO)
    solicitud = {
        "fecha": FECHA.isoformat(),
        "franja": "DIA",
        "motivo": "Necesidad operativa",
    }
    headers = {
        **token_guarderia(usuario),
        "Idempotency-Key": "emergencia-guarderia",
    }

    primera = client.post(RUTA_EMERGENCIA, json=solicitud, headers=headers)
    repetida = client.post(RUTA_EMERGENCIA, json=solicitud, headers=headers)

    assert primera.status_code == 200
    assert primera.json()["habilitadas"] == 1
    assert primera.json()["publico"] == primera.json()["cupo_maximo"]
    assert repetida.status_code == 200
    assert repetida.json()["habilitadas"] == 1


@pytest.mark.parametrize("rol", [Rol.PERSONAL, Rol.VETERINARIO])
def test_solo_duenio_puede_habilitar_emergencia(
    client,
    sembrar_cupo,
    crear_usuario,
    token_guarderia,
    rol: Rol,
) -> None:
    usuario = crear_usuario(rol)

    respuesta = client.post(
        RUTA_EMERGENCIA,
        json={
            "fecha": FECHA.isoformat(),
            "franja": "DIA",
            "motivo": "Necesidad operativa",
        },
        headers={
            **token_guarderia(usuario),
            "Idempotency-Key": f"emergencia-{rol.value.lower()}",
        },
    )

    assert respuesta.status_code == 403


def test_habilitar_emergencia_exige_motivo(
    client,
    sembrar_cupo,
    crear_usuario,
    token_guarderia,
) -> None:
    usuario = crear_usuario(Rol.DUENIO)

    respuesta = client.post(
        RUTA_EMERGENCIA,
        json={"fecha": FECHA.isoformat(), "franja": "DIA", "motivo": "  "},
        headers={
            **token_guarderia(usuario),
            "Idempotency-Key": "emergencia-sin-motivo",
        },
    )

    assert respuesta.status_code == 422
