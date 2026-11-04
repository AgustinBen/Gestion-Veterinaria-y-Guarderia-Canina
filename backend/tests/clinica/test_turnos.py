from datetime import date, datetime, time, timedelta

from app.core import parametros
from app.modules.clinica import service as clinica_service
from app.modules.clinica.models import TipoAtencion
from app.modules.clinica.schemas import AtencionCrear
from app.modules.identidad.permisos import Rol


def _lunes_futuro() -> date:
    hoy = date.today()
    dias_hasta_lunes = (7 - hoy.weekday()) % 7 or 7
    return hoy + timedelta(days=dias_hasta_lunes)


def _sembrar_horario_lunes(client, headers) -> None:
    respuesta = client.put(
        "/api/clinica/horarios",
        headers=headers,
        json=[
            {"dia_semana": 0, "hora_desde": "09:00", "hora_hasta": "13:00"},
            {"dia_semana": 0, "hora_desde": "16:00", "hora_hasta": "20:00"},
        ],
    )
    assert respuesta.status_code == 200


def _crear_turno(client, headers, paciente_id, veterinario_id, inicio, fin):
    return client.post(
        "/api/turnos",
        headers=headers,
        json={
            "paciente_id": paciente_id,
            "tipo": "CONSULTA",
            "veterinario_empleado_id": veterinario_id,
            "inicio": inicio.isoformat(),
            "fin": fin.isoformat(),
            "monto_centavos": 100000,
        },
    )


def test_agenda_medica_valida_horario_y_dia_sin_atencion(
    client, crear_usuario_clinica, clinica_context
) -> None:
    _, headers = crear_usuario_clinica(Rol.DUENIO)
    _sembrar_horario_lunes(client, headers)
    lunes = _lunes_futuro()

    aceptado = _crear_turno(
        client,
        headers,
        clinica_context["paciente_id"],
        clinica_context["veterinario_id"],
        datetime.combine(lunes, time(10)),
        datetime.combine(lunes, time(10, 30)),
    )
    assert aceptado.status_code == 201

    for inicio, fin in (
        (time(12, 45), time(13, 15)),
        (time(13), time(16)),
    ):
        fuera = _crear_turno(
            client,
            headers,
            clinica_context["paciente_id"],
            clinica_context["veterinario_id"],
            datetime.combine(lunes, inicio),
            datetime.combine(lunes, fin),
        )
        assert fuera.status_code == 422
        assert fuera.json()["detail"]["codigo"] == "FUERA_DE_HORARIO"
        assert fuera.json()["detail"]["mensaje"] == (
            "La clínica no atiende en ese horario. "
            "Por favor seleccione un horario válido"
        )

    domingo = lunes + timedelta(days=6)
    sin_horario = _crear_turno(
        client,
        headers,
        clinica_context["paciente_id"],
        clinica_context["veterinario_id"],
        datetime.combine(domingo, time(10)),
        datetime.combine(domingo, time(10, 30)),
    )
    assert sin_horario.status_code == 422


def test_agendar_sin_horarios_configurados_responde_conflicto(
    client, crear_usuario_clinica, clinica_context
) -> None:
    _, headers = crear_usuario_clinica(Rol.DUENIO)
    lunes = _lunes_futuro()
    respuesta = _crear_turno(
        client,
        headers,
        clinica_context["paciente_id"],
        clinica_context["veterinario_id"],
        datetime.combine(lunes, time(10)),
        datetime.combine(lunes, time(10, 30)),
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["codigo"] == "HORARIO_NO_DEFINIDO"


def test_solapamientos_bordes_y_cancelacion_liberan_horario(
    client, crear_usuario_clinica, clinica_context
) -> None:
    _, headers = crear_usuario_clinica(Rol.DUENIO)
    _sembrar_horario_lunes(client, headers)
    lunes = _lunes_futuro()
    inicio = datetime.combine(lunes, time(10))
    veterinario_id = clinica_context["veterinario_id"]
    paciente_id = clinica_context["paciente_id"]

    primero = _crear_turno(
        client, headers, paciente_id, veterinario_id, inicio, inicio + timedelta(minutes=30)
    )
    solapado = _crear_turno(
        client,
        headers,
        paciente_id,
        veterinario_id,
        inicio + timedelta(minutes=15),
        inicio + timedelta(minutes=45),
    )
    pegado = _crear_turno(
        client,
        headers,
        paciente_id,
        veterinario_id,
        inicio + timedelta(minutes=30),
        inicio + timedelta(minutes=60),
    )
    assert primero.status_code == 201
    assert solapado.status_code == 409
    assert solapado.json()["detail"]["codigo"] == "SOLAPADO"
    assert pegado.status_code == 201

    cancelado = client.post(
        f"/api/turnos/{primero.json()['id']}/cancelar",
        headers=headers,
        json={"motivo": "Reprogramación solicitada"},
    )
    assert cancelado.status_code == 200
    reutilizado = _crear_turno(
        client, headers, paciente_id, veterinario_id, inicio, inicio + timedelta(minutes=30)
    )
    assert reutilizado.status_code == 201


def test_reprogramar_turno_revalida_horario_y_estado(
    client, crear_usuario_clinica, clinica_context
) -> None:
    _, headers = crear_usuario_clinica(Rol.DUENIO)
    _sembrar_horario_lunes(client, headers)
    lunes = _lunes_futuro()
    inicio = datetime.combine(lunes, time(10))
    creado = _crear_turno(
        client,
        headers,
        clinica_context["paciente_id"],
        clinica_context["veterinario_id"],
        inicio,
        inicio + timedelta(minutes=30),
    )
    turno_id = creado.json()["id"]

    reprogramado = client.patch(
        f"/api/turnos/{turno_id}",
        headers=headers,
        json={
            "inicio": datetime.combine(lunes, time(11)).isoformat(),
            "fin": datetime.combine(lunes, time(11, 30)).isoformat(),
        },
    )
    assert reprogramado.status_code == 200
    assert reprogramado.json()["inicio"].startswith(
        datetime.combine(lunes, time(11)).isoformat()
    )

    fuera_de_horario = client.patch(
        f"/api/turnos/{turno_id}",
        headers=headers,
        json={
            "inicio": datetime.combine(lunes, time(14)).isoformat(),
            "fin": datetime.combine(lunes, time(14, 30)).isoformat(),
        },
    )
    assert fuera_de_horario.status_code == 422

    cancelado = client.post(
        f"/api/turnos/{turno_id}/cancelar",
        headers=headers,
        json={"motivo": "No puede asistir"},
    )
    assert cancelado.status_code == 200
    reprogramar_cancelado = client.patch(
        f"/api/turnos/{turno_id}",
        headers=headers,
        json={
            "inicio": datetime.combine(lunes, time(12)).isoformat(),
            "fin": datetime.combine(lunes, time(12, 30)).isoformat(),
        },
    )
    assert reprogramar_cancelado.status_code == 409


def test_mismo_paciente_no_puede_solaparse_con_otro_veterinario(
    client, crear_usuario_clinica, clinica_context, db_session
) -> None:
    from app.modules.padron import schemas as padron_schemas
    from app.modules.padron import service as padron_service

    _, headers = crear_usuario_clinica(Rol.DUENIO)
    _sembrar_horario_lunes(client, headers)
    segundo_veterinario = padron_service.crear_empleado(
        db_session,
        padron_schemas.EmpleadoNuevo(
            persona=padron_schemas.PersonaNueva(
                nombre="Segundo",
                apellido="Veterinario",
                dni="20000005",
                telefonos=["11 5555-0005"],
            ),
            es_veterinario=True,
        ),
    )
    lunes = _lunes_futuro()
    inicio = datetime.combine(lunes, time(10))
    primera = _crear_turno(
        client,
        headers,
        clinica_context["paciente_id"],
        clinica_context["veterinario_id"],
        inicio,
        inicio + timedelta(minutes=30),
    )
    segunda = _crear_turno(
        client,
        headers,
        clinica_context["paciente_id"],
        segundo_veterinario.persona_id,
        inicio,
        inicio + timedelta(minutes=30),
    )

    assert primera.status_code == 201
    assert segunda.status_code == 409


def test_mismo_veterinario_no_puede_atender_dos_pacientes_a_la_vez(
    client, crear_usuario_clinica, clinica_context, db_session
) -> None:
    from app.modules.padron import schemas as padron_schemas
    from app.modules.padron import service as padron_service

    _, headers = crear_usuario_clinica(Rol.DUENIO)
    _sembrar_horario_lunes(client, headers)
    tutor = padron_service.crear_persona(
        db_session,
        padron_schemas.PersonaNueva(
            nombre="Otro",
            apellido="Tutor",
            dni="20000006",
            telefonos=["11 5555-0006"],
        ),
    )
    especie = next(
        item
        for item in padron_service.listar_especies(db_session)
        if item.nombre == "Perro"
    )
    paciente = padron_service.crear_paciente(
        db_session,
        padron_schemas.PacienteNuevo(
            nombre="Segundo paciente",
            especie_id=especie.id,
            titular_persona_id=tutor.id,
        ),
    )
    inicio = datetime.combine(_lunes_futuro(), time(10))
    primera = _crear_turno(
        client,
        headers,
        clinica_context["paciente_id"],
        clinica_context["veterinario_id"],
        inicio,
        inicio + timedelta(minutes=30),
    )
    segunda = _crear_turno(
        client,
        headers,
        paciente.id,
        clinica_context["veterinario_id"],
        inicio,
        inicio + timedelta(minutes=30),
    )

    assert primera.status_code == 201
    assert segunda.status_code == 409


def test_traspaso_bloquea_turnos_segun_parametro(
    client, crear_usuario_clinica, clinica_context, db_session
) -> None:
    _, headers = crear_usuario_clinica(Rol.DUENIO)
    horario = client.put(
        "/api/clinica/horarios",
        headers=headers,
        json=[
            {"dia_semana": 0, "hora_desde": "09:00", "hora_hasta": "20:00"},
        ],
    )
    assert horario.status_code == 200
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
    parametros.set_param(
        db_session,
        "clinica.traspaso_bloquea_turnos",
        True,
        "bool",
        modulo="clinica",
    )
    lunes = _lunes_futuro()
    inicio = datetime.combine(lunes, time(13, 40))
    bloqueo = _crear_turno(
        client,
        headers,
        clinica_context["paciente_id"],
        clinica_context["veterinario_id"],
        inicio,
        inicio + timedelta(minutes=20),
    )
    assert bloqueo.status_code == 409
    assert bloqueo.json()["detail"]["codigo"] == "TRASPASO_BLOQUEADO"

    parametros.set_param(
        db_session,
        "clinica.traspaso_bloquea_turnos",
        False,
        "bool",
        modulo="clinica",
    )
    permitido = _crear_turno(
        client,
        headers,
        clinica_context["paciente_id"],
        clinica_context["veterinario_id"],
        inicio,
        inicio + timedelta(minutes=20),
    )
    assert permitido.status_code == 201


def test_rechaza_empleados_no_validos_y_turnos_en_el_pasado(
    client, crear_usuario_clinica, clinica_context
) -> None:
    _, headers = crear_usuario_clinica(Rol.DUENIO)
    _sembrar_horario_lunes(client, headers)
    inicio = datetime.combine(_lunes_futuro(), time(10))

    for empleado_id in (
        clinica_context["cirujano_id"],
        clinica_context["personal_no_veterinario_id"],
    ):
        respuesta = _crear_turno(
            client,
            headers,
            clinica_context["paciente_id"],
            empleado_id,
            inicio,
            inicio + timedelta(minutes=30),
        )
        assert respuesta.status_code == 422

    pasado = datetime.now().replace(second=0, microsecond=0) - timedelta(days=1)
    respuesta_pasada = _crear_turno(
        client,
        headers,
        clinica_context["paciente_id"],
        clinica_context["veterinario_id"],
        pasado,
        pasado + timedelta(minutes=30),
    )
    assert respuesta_pasada.status_code == 422


def test_turno_atendido_guarda_atencion_y_no_se_puede_cancelar(
    client, crear_usuario_clinica, clinica_context, db_session
) -> None:
    usuario, headers = crear_usuario_clinica(Rol.DUENIO)
    _sembrar_horario_lunes(client, headers)
    lunes = _lunes_futuro()
    inicio = datetime.combine(lunes, time(10))
    respuesta = _crear_turno(
        client,
        headers,
        clinica_context["paciente_id"],
        clinica_context["veterinario_id"],
        inicio,
        inicio + timedelta(minutes=30),
    )
    atencion = clinica_service.registrar_atencion(
        db_session,
        clinica_context["paciente_id"],
        AtencionCrear(
            tipo=TipoAtencion.CONSULTA,
            fecha_hora=inicio,
            veterinario_empleado_id=clinica_context["veterinario_id"],
        ),
        created_by=usuario.id,
    )

    atendido = client.post(
        f"/api/turnos/{respuesta.json()['id']}/atendido",
        headers=headers,
        json={"atencion_id": atencion.id},
    )
    assert atendido.status_code == 200
    assert atendido.json()["atencion_id"] == atencion.id

    cancelar = client.post(
        f"/api/turnos/{respuesta.json()['id']}/cancelar",
        headers=headers,
        json={"motivo": "Ya atendido"},
    )
    assert cancelar.status_code == 409

    segundo_turno = _crear_turno(
        client,
        headers,
        clinica_context["paciente_id"],
        clinica_context["veterinario_id"],
        inicio + timedelta(hours=1),
        inicio + timedelta(hours=1, minutes=30),
    )
    atendido_sin_atencion = client.post(
        f"/api/turnos/{segundo_turno.json()['id']}/atendido",
        headers=headers,
    )
    assert atendido_sin_atencion.status_code == 200
    assert atendido_sin_atencion.json()["atencion_id"] is None


def test_marcar_ausente_es_un_estado_terminal(
    client, crear_usuario_clinica, clinica_context
) -> None:
    _, headers = crear_usuario_clinica(Rol.DUENIO)
    _sembrar_horario_lunes(client, headers)
    inicio = datetime.combine(_lunes_futuro(), time(10))
    creado = _crear_turno(
        client,
        headers,
        clinica_context["paciente_id"],
        clinica_context["veterinario_id"],
        inicio,
        inicio + timedelta(minutes=30),
    )
    ausente = client.post(
        f"/api/turnos/{creado.json()['id']}/ausente",
        headers=headers,
    )
    assert ausente.status_code == 200
    assert ausente.json()["estado"] == "AUSENTE"
    cancelar = client.post(
        f"/api/turnos/{creado.json()['id']}/cancelar",
        headers=headers,
        json={"motivo": "No se presentó"},
    )
    assert cancelar.status_code == 409


def test_matriz_de_permisos_de_turnos_medicos(
    client, crear_usuario_clinica, clinica_context
) -> None:
    _headers = {
        rol: crear_usuario_clinica(rol)[1]
        for rol in (Rol.DUENIO, Rol.PERSONAL, Rol.VETERINARIO)
    }
    _sembrar_horario_lunes(client, _headers[Rol.DUENIO])
    lunes = _lunes_futuro()

    for numero, rol in enumerate((Rol.DUENIO, Rol.PERSONAL, Rol.VETERINARIO)):
        inicio = datetime.combine(lunes, time(10 + numero))
        respuesta = _crear_turno(
            client,
            _headers[rol],
            clinica_context["paciente_id"],
            clinica_context["veterinario_id"],
            inicio,
            inicio + timedelta(minutes=30),
        )
        # El veterinario atiende turnos pero no los agenda.
        assert respuesta.status_code == (
            403 if rol == Rol.VETERINARIO else 201
        )

    sin_token = client.post(
        "/api/turnos",
        json={
            "paciente_id": clinica_context["paciente_id"],
            "tipo": "CONSULTA",
            "veterinario_empleado_id": clinica_context["veterinario_id"],
            "inicio": datetime.combine(lunes, time(15)).isoformat(),
            "fin": datetime.combine(lunes, time(15, 30)).isoformat(),
        },
    )
    assert sin_token.status_code == 401
