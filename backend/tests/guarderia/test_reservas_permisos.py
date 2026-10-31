from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.modules.identidad.permisos import Rol


def _payload(tutor_id: int, paciente_id: int) -> dict[str, object]:
    fecha = date.today() + timedelta(days=2)
    return {
        "tutor_persona_id": tutor_id,
        "paciente_ids": [paciente_id],
        "desde_fecha": fecha.isoformat(),
        "desde_franja": "DIA",
        "hasta_fecha": fecha.isoformat(),
        "hasta_franja": "DIA",
        "cuidados_extras": [
            {"paciente_id": paciente_id, "cuidados_extras": False}
        ],
        "total_centavos": 300000,
    }


def _assert_crear_y_registrar_sena(
    client,
    sembrar_cupo,
    crear_datos_reserva,
    crear_usuario,
    token_guarderia,
    rol: Rol,
) -> None:
    datos = crear_datos_reserva()
    usuario = crear_usuario(rol)
    headers = token_guarderia(usuario)
    creada = client.post(
        "/api/guarderia/reservas",
        json=_payload(datos.tutor_persona_id, datos.paciente_ids[0]),
        headers={**headers, "Idempotency-Key": f"reserva-{rol.value}"},
    )
    sena = client.post(
        f"/api/guarderia/reservas/{creada.json()['id']}/sena",
        json={"monto_centavos": 100000, "medio": "EFECTIVO"},
        headers={**headers, "Idempotency-Key": f"sena-{rol.value}"},
    )

    assert creada.status_code == 201
    assert sena.status_code == 200


@pytest.mark.parametrize("rol", [Rol.DUENIO, Rol.PERSONAL])
def test_permisos_escritura_para_duenio_y_personal(
    client,
    sembrar_cupo,
    crear_datos_reserva,
    crear_usuario,
    token_guarderia,
    rol: Rol,
) -> None:
    _assert_crear_y_registrar_sena(
        client,
        sembrar_cupo,
        crear_datos_reserva,
        crear_usuario,
        token_guarderia,
        rol,
    )


def test_veterinario_solo_lectura_para_reservas(
    client,
    sembrar_cupo,
    crear_datos_reserva,
    crear_usuario,
    token_guarderia,
) -> None:
    datos = crear_datos_reserva()
    duenio = crear_usuario(Rol.DUENIO)
    headers_duenio = token_guarderia(duenio)
    creada = client.post(
        "/api/guarderia/reservas",
        json=_payload(datos.tutor_persona_id, datos.paciente_ids[0]),
        headers={**headers_duenio, "Idempotency-Key": "vet-read-reserva"},
    )
    veterinario = crear_usuario(Rol.VETERINARIO)
    headers_veterinario = token_guarderia(veterinario)

    lectura_detalle = client.get(
        f"/api/guarderia/reservas/{creada.json()['id']}",
        headers=headers_veterinario,
    )
    lectura_lista = client.get(
        "/api/guarderia/reservas",
        headers=headers_veterinario,
    )
    escritura_reserva = client.post(
        "/api/guarderia/reservas",
        json=_payload(datos.tutor_persona_id, datos.paciente_ids[0]),
        headers={**headers_veterinario, "Idempotency-Key": "vet-write-reserva"},
    )
    escritura_sena = client.post(
        f"/api/guarderia/reservas/{creada.json()['id']}/sena",
        json={"monto_centavos": 100000, "medio": "EFECTIVO"},
        headers={**headers_veterinario, "Idempotency-Key": "vet-write-sena"},
    )

    assert lectura_detalle.status_code == 200
    assert lectura_lista.status_code == 200
    assert escritura_reserva.status_code == 403
    assert escritura_sena.status_code == 403


def test_escrituras_y_lecturas_requieren_token(
    client,
    sembrar_cupo,
    crear_datos_reserva,
) -> None:
    datos = crear_datos_reserva()
    cuerpo = _payload(datos.tutor_persona_id, datos.paciente_ids[0])

    crear = client.post(
        "/api/guarderia/reservas",
        json=cuerpo,
        headers={"Idempotency-Key": "sin-token"},
    )
    listar = client.get("/api/guarderia/reservas")

    assert crear.status_code == 401
    assert listar.status_code == 401
