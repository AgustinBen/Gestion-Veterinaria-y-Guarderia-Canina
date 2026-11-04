from datetime import date, datetime, time, timedelta

from app.modules.identidad.permisos import Rol
from app.modules.padron import schemas as padron_schemas
from app.modules.padron import service as padron_service


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


def _crear_cirugia(
    client,
    headers,
    *,
    paciente_id: int,
    veterinario_id: int,
    externo_id: int,
    inicio: datetime,
    minutos: int = 30,
):
    return client.post(
        "/api/turnos",
        headers=headers,
        json={
            "paciente_id": paciente_id,
            "tipo": "CIRUGIA",
            "veterinario_empleado_id": veterinario_id,
            "externo_empleado_id": externo_id,
            "inicio": inicio.isoformat(),
            "fin": (inicio + timedelta(minutes=minutos)).isoformat(),
            "monto_centavos": 100000,
        },
    )


def _confirmar(client, headers, turno_id: int, costo_centavos: int):
    return client.post(
        f"/api/turnos/{turno_id}/externo/confirmar",
        headers=headers,
        json={"costo_acordado_centavos": costo_centavos},
    )


def _crear_externo_extra(db_session, *, nombre: str, dni: str, telefono: str) -> int:
    empleado = padron_service.crear_empleado(
        db_session,
        padron_schemas.EmpleadoNuevo(
            persona=padron_schemas.PersonaNueva(
                nombre=nombre,
                apellido="Externo",
                dni=dni,
                telefonos=[telefono],
            ),
            tipo="EXTERNO",
            es_veterinario=True,
        ),
    )
    return empleado.persona_id


def _crear_veterinario_extra(db_session, *, nombre: str, dni: str, telefono: str) -> int:
    empleado = padron_service.crear_empleado(
        db_session,
        padron_schemas.EmpleadoNuevo(
            persona=padron_schemas.PersonaNueva(
                nombre=nombre,
                apellido="Veterinario",
                dni=dni,
                telefonos=[telefono],
            ),
            es_veterinario=True,
        ),
    )
    return empleado.persona_id


def _crear_paciente_extra(db_session, *, nombre: str, dni: str, telefono: str) -> int:
    tutor = padron_service.crear_persona(
        db_session,
        padron_schemas.PersonaNueva(
            nombre="Tutor",
            apellido=nombre,
            dni=dni,
            telefonos=[telefono],
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
            nombre=nombre,
            especie_id=especie.id,
            titular_persona_id=tutor.id,
        ),
    )
    return paciente.id


def test_flujo_contacto_confirmacion_rechazo_y_reemplazo(
    client, crear_usuario_clinica, clinica_context, db_session
) -> None:
    usuario, headers = crear_usuario_clinica(Rol.DUENIO)
    _sembrar_horario(client, headers)
    lunes = _lunes_futuro()

    primero = _crear_cirugia(
        client,
        headers,
        paciente_id=clinica_context["paciente_id"],
        veterinario_id=clinica_context["veterinario_id"],
        externo_id=clinica_context["cirujano_id"],
        inicio=datetime.combine(lunes, time(10)),
    )
    turno_id = primero.json()["id"]

    contactado = client.post(
        f"/api/turnos/{turno_id}/externo/contactado",
        headers=headers,
        json={"medio": "TELEFONO", "nota": "Se dejó mensaje"},
    )
    assert contactado.status_code == 201
    assert contactado.json()["tipo"] == "CONTACTADO"
    assert contactado.json()["usuario_id"] == usuario.id
    assert contactado.json()["created_at"] is not None
    assert contactado.json()["medio"] == "TELEFONO"

    confirmado = _confirmar(client, headers, turno_id, 40000)
    assert confirmado.status_code == 201
    assert confirmado.json()["tipo"] == "CONFIRMADO"
    assert confirmado.json()["costo_acordado_centavos"] == 40000

    turno = client.get(f"/api/turnos/{turno_id}", headers=headers)
    assert turno.json()["estado"] == "CONFIRMADO"

    linea = client.get(f"/api/turnos/{turno_id}/externo", headers=headers)
    assert linea.status_code == 200
    assert [evento["tipo"] for evento in linea.json()] == [
        "CONTACTADO",
        "CONFIRMADO",
    ]

    rechazo = _crear_cirugia(
        client,
        headers,
        paciente_id=clinica_context["paciente_id"],
        veterinario_id=clinica_context["veterinario_id"],
        externo_id=clinica_context["cirujano_id"],
        inicio=datetime.combine(lunes, time(11)),
    )
    rechazado = client.post(
        f"/api/turnos/{rechazo.json()['id']}/externo/rechazar",
        headers=headers,
        json={"motivo": "No puede ese día"},
    )
    assert rechazado.status_code == 201
    assert rechazado.json()["tipo"] == "RECHAZADO"
    turno_rechazado = client.get(
        f"/api/turnos/{rechazo.json()['id']}", headers=headers
    )
    assert turno_rechazado.json()["estado"] == "PENDIENTE_EXTERNO"

    nuevo_externo = _crear_externo_extra(
        db_session,
        nombre="Nuevo",
        dni="20000011",
        telefono="11 5555-0011",
    )
    reemplazo = _crear_cirugia(
        client,
        headers,
        paciente_id=clinica_context["paciente_id"],
        veterinario_id=clinica_context["veterinario_id"],
        externo_id=clinica_context["cirujano_id"],
        inicio=datetime.combine(lunes, time(12)),
    )
    reemplazado = client.post(
        f"/api/turnos/{reemplazo.json()['id']}/externo/reemplazar",
        headers=headers,
        json={"externo_empleado_id": nuevo_externo},
    )
    assert reemplazado.status_code == 201
    assert reemplazado.json()["tipo"] == "REEMPLAZADO"
    assert reemplazado.json()["externo_empleado_id"] == nuevo_externo
    turno_reemplazado = client.get(
        f"/api/turnos/{reemplazo.json()['id']}", headers=headers
    )
    assert turno_reemplazado.json()["externo_actual_id"] == nuevo_externo

    no_reemplaza_confirmado = client.post(
        f"/api/turnos/{turno_id}/externo/reemplazar",
        headers=headers,
        json={"externo_empleado_id": nuevo_externo},
    )
    assert no_reemplaza_confirmado.status_code == 409


def test_confirmar_rechaza_costos_invalidos(
    client, crear_usuario_clinica, clinica_context
) -> None:
    _, headers = crear_usuario_clinica(Rol.DUENIO)
    _sembrar_horario(client, headers)
    creado = _crear_cirugia(
        client,
        headers,
        paciente_id=clinica_context["paciente_id"],
        veterinario_id=clinica_context["veterinario_id"],
        externo_id=clinica_context["cirujano_id"],
        inicio=datetime.combine(_lunes_futuro(), time(10)),
    )
    turno_id = creado.json()["id"]

    for costo in (0, -1, 100.5):
        respuesta = _confirmar(client, headers, turno_id, costo)
        assert respuesta.status_code == 422

    turno = client.get(f"/api/turnos/{turno_id}", headers=headers)
    assert turno.json()["estado"] == "PENDIENTE_EXTERNO"
    linea = client.get(f"/api/turnos/{turno_id}/externo", headers=headers)
    assert linea.json() == []


def test_confirmar_externo_ocupado_por_otra_cirugia(
    client, crear_usuario_clinica, clinica_context, db_session
) -> None:
    _, headers = crear_usuario_clinica(Rol.DUENIO)
    _sembrar_horario(client, headers)
    lunes = _lunes_futuro()
    otro_veterinario = _crear_veterinario_extra(
        db_session,
        nombre="Segundo",
        dni="20000012",
        telefono="11 5555-0012",
    )
    otro_paciente = _crear_paciente_extra(
        db_session,
        nombre="Otro paciente",
        dni="20000013",
        telefono="11 5555-0013",
    )

    primera = _crear_cirugia(
        client,
        headers,
        paciente_id=clinica_context["paciente_id"],
        veterinario_id=clinica_context["veterinario_id"],
        externo_id=clinica_context["cirujano_id"],
        inicio=datetime.combine(lunes, time(10)),
    )
    segunda = _crear_cirugia(
        client,
        headers,
        paciente_id=otro_paciente,
        veterinario_id=otro_veterinario,
        externo_id=clinica_context["cirujano_id"],
        inicio=datetime.combine(lunes, time(10, 15)),
    )
    assert primera.status_code == 201
    assert segunda.status_code == 201

    assert _confirmar(client, headers, primera.json()["id"], 40000).status_code == 201
    ocupado = _confirmar(client, headers, segunda.json()["id"], 40000)
    assert ocupado.status_code == 409
    assert ocupado.json()["detail"]["codigo"] == "EXTERNO_OCUPADO"

    segunda_turno = client.get(f"/api/turnos/{segunda.json()['id']}", headers=headers)
    assert segunda_turno.json()["estado"] == "PENDIENTE_EXTERNO"


def test_eventos_sin_endpoint_de_borrado_y_sin_token(
    client, crear_usuario_clinica, clinica_context
) -> None:
    _, headers = crear_usuario_clinica(Rol.DUENIO)
    _sembrar_horario(client, headers)
    creado = _crear_cirugia(
        client,
        headers,
        paciente_id=clinica_context["paciente_id"],
        veterinario_id=clinica_context["veterinario_id"],
        externo_id=clinica_context["cirujano_id"],
        inicio=datetime.combine(_lunes_futuro(), time(10)),
    )
    turno_id = creado.json()["id"]

    assert client.delete(f"/api/turnos/{turno_id}/externo").status_code == 405
    assert client.put(f"/api/turnos/{turno_id}/externo").status_code == 405

    assert client.get(f"/api/turnos/{turno_id}/externo").status_code == 401
    assert (
        client.post(
            f"/api/turnos/{turno_id}/externo/contactado",
            json={"medio": "TELEFONO"},
        ).status_code
        == 401
    )
    assert (
        client.post(
            f"/api/turnos/{turno_id}/externo/confirmar",
            json={"costo_acordado_centavos": 40000},
        ).status_code
        == 401
    )
    assert (
        client.post(
            f"/api/turnos/{turno_id}/externo/rechazar",
            json={"motivo": "No puede"},
        ).status_code
        == 401
    )
    assert (
        client.post(
            f"/api/turnos/{turno_id}/externo/reemplazar",
            json={"externo_empleado_id": clinica_context["cirujano_id"]},
        ).status_code
        == 401
    )
