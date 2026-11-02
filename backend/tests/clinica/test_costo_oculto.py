from datetime import date, datetime, time, timedelta

from app.modules.identidad.permisos import Rol


def _lunes_futuro() -> date:
    hoy = date.today()
    dias_hasta_lunes = (7 - hoy.weekday()) % 7 or 7
    return hoy + timedelta(days=dias_hasta_lunes)


def _sembrar_horario(client, headers) -> None:
    respuesta = client.put(
        "/api/clinica/horarios",
        headers=headers,
        json=[{"dia_semana": 0, "hora_desde": "09:00", "hora_hasta": "20:00"}],
    )
    assert respuesta.status_code == 200


def _crear_cirugia(client, headers, *, paciente_id, veterinario_id, externo_id, inicio):
    return client.post(
        "/api/turnos",
        headers=headers,
        json={
            "paciente_id": paciente_id,
            "tipo": "CIRUGIA",
            "veterinario_empleado_id": veterinario_id,
            "externo_empleado_id": externo_id,
            "inicio": inicio.isoformat(),
            "fin": (inicio + timedelta(minutes=30)).isoformat(),
        },
    )


def _confirmar(client, headers, turno_id: int, costo_centavos: int):
    return client.post(
        f"/api/turnos/{turno_id}/externo/confirmar",
        headers=headers,
        json={"costo_acordado_centavos": costo_centavos},
    )


def test_costo_oculto_para_personal_y_veterinario(
    client, crear_usuario_clinica, clinica_context
) -> None:
    _, headers_duenio = crear_usuario_clinica(Rol.DUENIO)
    _, headers_personal = crear_usuario_clinica(Rol.PERSONAL)
    _, headers_veterinario = crear_usuario_clinica(Rol.VETERINARIO)
    _sembrar_horario(client, headers_duenio)
    lunes = _lunes_futuro()

    turno_duenio = _crear_cirugia(
        client,
        headers_duenio,
        paciente_id=clinica_context["paciente_id"],
        veterinario_id=clinica_context["veterinario_id"],
        externo_id=clinica_context["cirujano_id"],
        inicio=datetime.combine(lunes, time(10)),
    )
    turno_personal = _crear_cirugia(
        client,
        headers_duenio,
        paciente_id=clinica_context["paciente_id"],
        veterinario_id=clinica_context["veterinario_id"],
        externo_id=clinica_context["cirujano_id"],
        inicio=datetime.combine(lunes, time(11)),
    )
    turno_veterinario = _crear_cirugia(
        client,
        headers_duenio,
        paciente_id=clinica_context["paciente_id"],
        veterinario_id=clinica_context["veterinario_id"],
        externo_id=clinica_context["cirujano_id"],
        inicio=datetime.combine(lunes, time(12)),
    )

    confirmado_duenio = _confirmar(
        client, headers_duenio, turno_duenio.json()["id"], 40000
    )
    assert confirmado_duenio.status_code == 201
    assert confirmado_duenio.json()["costo_acordado_centavos"] == 40000
    assert confirmado_duenio.json()["costo_registrado"] is True

    confirmado_personal = _confirmar(
        client, headers_personal, turno_personal.json()["id"], 41000
    )
    assert confirmado_personal.status_code == 201
    assert "costo_acordado_centavos" in confirmado_personal.json()
    assert confirmado_personal.json()["costo_acordado_centavos"] is None
    assert confirmado_personal.json()["costo_registrado"] is True

    confirmado_veterinario = _confirmar(
        client, headers_veterinario, turno_veterinario.json()["id"], 42000
    )
    assert confirmado_veterinario.status_code == 201
    assert confirmado_veterinario.json()["costo_acordado_centavos"] is None
    assert confirmado_veterinario.json()["costo_registrado"] is True

    linea_personal = client.get(
        f"/api/turnos/{turno_duenio.json()['id']}/externo",
        headers=headers_personal,
    )
    evento_confirmado = next(
        evento
        for evento in linea_personal.json()
        if evento["tipo"] == "CONFIRMADO"
    )
    assert evento_confirmado["costo_acordado_centavos"] is None
    assert evento_confirmado["costo_registrado"] is True

    linea_duenio = client.get(
        f"/api/turnos/{turno_duenio.json()['id']}/externo",
        headers=headers_duenio,
    )
    evento_confirmado_duenio = next(
        evento for evento in linea_duenio.json() if evento["tipo"] == "CONFIRMADO"
    )
    assert evento_confirmado_duenio["costo_acordado_centavos"] == 40000

    linea_veterinario = client.get(
        f"/api/turnos/{turno_personal.json()['id']}/externo",
        headers=headers_veterinario,
    )
    evento_confirmado_veterinario = next(
        evento
        for evento in linea_veterinario.json()
        if evento["tipo"] == "CONFIRMADO"
    )
    assert evento_confirmado_veterinario["costo_acordado_centavos"] is None

    linea_duenio_personal = client.get(
        f"/api/turnos/{turno_personal.json()['id']}/externo",
        headers=headers_duenio,
    )
    evento_duenio_personal = next(
        evento
        for evento in linea_duenio_personal.json()
        if evento["tipo"] == "CONFIRMADO"
    )
    assert evento_duenio_personal["costo_acordado_centavos"] == 41000
