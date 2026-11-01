from app.modules.identidad.permisos import Rol


def test_matriz_de_permisos_de_historia_clinica(
    client, clinica_context, crear_usuario_clinica
) -> None:
    path = f"/api/pacientes/{clinica_context['paciente_id']}/atenciones"
    payload = {
        "tipo": "CONSULTA",
        "veterinario_empleado_id": clinica_context["veterinario_id"],
    }
    _, duenio_headers = crear_usuario_clinica(Rol.DUENIO)
    _, veterinario_headers = crear_usuario_clinica(
        Rol.VETERINARIO,
        empleado_id=clinica_context["veterinario_id"],
    )
    _, personal_headers = crear_usuario_clinica(Rol.PERSONAL)

    assert client.post(path, json=payload, headers=duenio_headers).status_code == 201
    assert (
        client.post(path, json=payload, headers=veterinario_headers).status_code
        == 201
    )
    assert client.post(path, json=payload, headers=personal_headers).status_code == 403
    assert client.get(path, headers=personal_headers).status_code == 200
    assert client.get(path).status_code == 401
    assert client.post(path, json=payload).status_code == 401
