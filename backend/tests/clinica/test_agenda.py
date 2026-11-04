from datetime import date, datetime, time, timedelta

from app.modules.identidad.permisos import Rol


def _lunes_futuro() -> date:
    hoy = date.today()
    dias_hasta_lunes = (7 - hoy.weekday()) % 7 or 7
    return hoy + timedelta(days=dias_hasta_lunes)


def test_agenda_combina_turnos_horarios_personal_y_traspasos(
    client, crear_usuario_clinica, clinica_context
) -> None:
    _, headers = crear_usuario_clinica(Rol.DUENIO)
    lunes = _lunes_futuro()
    assert client.put(
        "/api/clinica/horarios",
        headers=headers,
        json=[
            {"dia_semana": 0, "hora_desde": "09:00", "hora_hasta": "13:00"},
            {"dia_semana": 0, "hora_desde": "16:00", "hora_hasta": "20:00"},
        ],
    ).status_code == 200
    definicion = client.put(
        "/api/clinica/turnos-personal/definicion",
        headers=headers,
        json={
            "turnos": [
                {"turno": "MANANA", "hora_desde": "06:00", "hora_hasta": "14:00"},
                {"turno": "TARDE", "hora_desde": "14:00", "hora_hasta": "22:00"},
                {"turno": "NOCHE", "hora_desde": "22:00", "hora_hasta": "06:00"},
            ]
        },
    )
    assert definicion.status_code == 200

    fecha_anterior = lunes - timedelta(days=1)
    asignaciones = [
        {
            "empleado_id": clinica_context["veterinario_id"],
            "fecha": fecha.isoformat(),
            "turno": franja,
        }
        for fecha, franja in (
            (fecha_anterior, "NOCHE"),
            (lunes, "MANANA"),
            (lunes, "TARDE"),
            (lunes, "NOCHE"),
        )
    ]
    for asignacion in asignaciones:
        assert (
            client.post(
                "/api/clinica/turnos-personal",
                headers=headers,
                json=asignacion,
            ).status_code
            == 201
        )

    inicio = datetime.combine(lunes, time(10))
    turno = client.post(
        "/api/turnos",
        headers=headers,
        json={
            "paciente_id": clinica_context["paciente_id"],
            "tipo": "CONSULTA",
            "veterinario_empleado_id": clinica_context["veterinario_id"],
            "inicio": inicio.isoformat(),
            "fin": (inicio + timedelta(minutes=30)).isoformat(),
            "monto_centavos": 100000,
        },
    )
    assert turno.status_code == 201

    respuesta = client.get(
        "/api/clinica/agenda",
        headers=headers,
        params={
            "desde": lunes.isoformat(),
            "hasta": lunes.isoformat(),
            "veterinario_id": clinica_context["veterinario_id"],
        },
    )

    assert respuesta.status_code == 200
    dia = respuesta.json()[0]
    assert len(dia["horarios_atencion"]) == 2
    assert [item["id"] for item in dia["turnos"]] == [turno.json()["id"]]
    assert len(dia["turnos_personal"]) == 3
    assert len(dia["ventanas_traspaso"]) == 3
    assert dia["ventanas_traspaso"][2]["inicio"].startswith(lunes.isoformat())
    assert dia["ventanas_traspaso"][2]["empleados_salen"][0]["empleado_id"] == (
        clinica_context["veterinario_id"]
    )


def test_agenda_sin_turnos_devuelve_dias_vacios(
    client, crear_usuario_clinica
) -> None:
    _, headers = crear_usuario_clinica(Rol.DUENIO)
    hoy = date.today()

    respuesta = client.get(
        "/api/clinica/agenda",
        headers=headers,
        params={"desde": hoy.isoformat(), "hasta": hoy.isoformat()},
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == [
        {
            "fecha": hoy.isoformat(),
            "horarios_atencion": [],
            "turnos": [],
            "turnos_personal": [],
            "ventanas_traspaso": [],
        }
    ]


def test_veterinarios_de_agenda_requiere_rol_y_perfil_clinico(
    client, crear_usuario_clinica, clinica_context
) -> None:
    crear_usuario_clinica(
        Rol.VETERINARIO,
        empleado_id=clinica_context["veterinario_id"],
    )
    crear_usuario_clinica(
        Rol.VETERINARIO,
        empleado_id=clinica_context["personal_no_veterinario_id"],
    )
    _, headers = crear_usuario_clinica(Rol.PERSONAL)

    respuesta = client.get("/api/clinica/veterinarios", headers=headers)

    assert respuesta.status_code == 200
    assert respuesta.json() == [clinica_context["veterinario_id"]]
