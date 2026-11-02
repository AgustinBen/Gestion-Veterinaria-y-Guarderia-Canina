from datetime import date, timedelta

from app.modules.identidad.permisos import Rol


def test_asignar_turno_personal_permisos_duplicado_y_empleado_externo(
    client, crear_usuario_clinica, clinica_context
) -> None:
    _, duenio = crear_usuario_clinica(Rol.DUENIO)
    _, personal = crear_usuario_clinica(Rol.PERSONAL)
    _, veterinario = crear_usuario_clinica(Rol.VETERINARIO)
    for headers in (duenio, personal, veterinario):
        assert (
            client.get(
                "/api/clinica/turnos-personal/definicion",
                headers=headers,
            ).status_code
            == 200
        )
    datos = {
        "empleado_id": clinica_context["veterinario_id"],
        "fecha": (date.today() + timedelta(days=14)).isoformat(),
        "turno": "MANANA",
    }

    creado = client.post(
        "/api/clinica/turnos-personal",
        headers=duenio,
        json=datos,
    )
    assert creado.status_code == 201
    assert client.get("/api/clinica/turnos-personal", headers=personal).status_code == 200
    assert client.get("/api/clinica/turnos-personal", headers=veterinario).status_code == 200

    duplicado = client.post(
        "/api/clinica/turnos-personal",
        headers=duenio,
        json=datos,
    )
    assert duplicado.status_code == 409

    externo = client.post(
        "/api/clinica/turnos-personal",
        headers=duenio,
        json={
            **datos,
            "empleado_id": clinica_context["cirujano_id"],
            "turno": "TARDE",
        },
    )
    assert externo.status_code == 422

    for headers in (personal, veterinario):
        denegado = client.post(
            "/api/clinica/turnos-personal",
            headers=headers,
            json={**datos, "turno": "TARDE"},
        )
        assert denegado.status_code == 403
        definicion_denegada = client.put(
            "/api/clinica/turnos-personal/definicion",
            headers=headers,
            json={"turnos": []},
        )
        assert definicion_denegada.status_code == 403

    eliminado = client.delete(
        "/api/clinica/turnos-personal",
        headers=duenio,
        params=datos,
    )
    assert eliminado.status_code == 204
