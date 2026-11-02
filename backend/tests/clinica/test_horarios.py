from app.modules.identidad.permisos import Rol


def test_horarios_lectura_para_los_tres_roles_y_escritura_solo_duenio(
    client, crear_usuario_clinica
) -> None:
    headers = {
        rol: crear_usuario_clinica(rol)[1]
        for rol in (Rol.DUENIO, Rol.PERSONAL, Rol.VETERINARIO)
    }

    for autenticacion in headers.values():
        assert client.get("/api/clinica/horarios", headers=autenticacion).status_code == 200

    respuesta = client.put(
        "/api/clinica/horarios",
        headers=headers[Rol.DUENIO],
        json=[
            {"dia_semana": 0, "hora_desde": "09:00", "hora_hasta": "13:00"},
            {"dia_semana": 0, "hora_desde": "16:00", "hora_hasta": "20:00"},
        ],
    )
    assert respuesta.status_code == 200
    assert len(respuesta.json()) == 2

    for rol in (Rol.PERSONAL, Rol.VETERINARIO):
        denegada = client.put(
            "/api/clinica/horarios",
            headers=headers[rol],
            json=[],
        )
        assert denegada.status_code == 403


def test_horarios_rechaza_franjas_superpuestas(client, crear_usuario_clinica) -> None:
    _, headers = crear_usuario_clinica(Rol.DUENIO)
    respuesta = client.put(
        "/api/clinica/horarios",
        headers=headers,
        json=[
            {"dia_semana": 0, "hora_desde": "09:00", "hora_hasta": "13:00"},
            {"dia_semana": 0, "hora_desde": "12:30", "hora_hasta": "14:00"},
        ],
    )

    assert respuesta.status_code == 422
