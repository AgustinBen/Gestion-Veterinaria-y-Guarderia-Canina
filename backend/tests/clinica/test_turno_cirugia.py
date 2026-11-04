from datetime import date, datetime, time, timedelta

from app.modules.clinica import service as clinica_service
from app.modules.clinica.models import TipoAtencion
from app.modules.clinica.schemas import AtencionCrear
from app.modules.cobros import service as cobros_service
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
            "fin": (inicio + timedelta(minutes=30)).isoformat(),
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


def test_creacion_cirugia_exige_externo_valido(
    client, crear_usuario_clinica, clinica_context
) -> None:
    _, headers = crear_usuario_clinica(Rol.DUENIO)
    _sembrar_horario(client, headers)
    inicio = datetime.combine(_lunes_futuro(), time(10))
    payload = {
        "paciente_id": clinica_context["paciente_id"],
        "tipo": "CIRUGIA",
        "veterinario_empleado_id": clinica_context["veterinario_id"],
        "inicio": inicio.isoformat(),
        "fin": (inicio + timedelta(minutes=30)).isoformat(),
        "monto_centavos": 100000,
    }

    sin_externo = client.post("/api/turnos", headers=headers, json=payload)
    assert sin_externo.status_code == 422

    interno = client.post(
        "/api/turnos",
        headers=headers,
        json={**payload, "externo_empleado_id": clinica_context["veterinario_id"]},
    )
    assert interno.status_code == 422
    assert interno.json()["detail"]["codigo"] == "EXTERNO_INVALIDO"

    valido = _crear_cirugia(
        client,
        headers,
        paciente_id=clinica_context["paciente_id"],
        veterinario_id=clinica_context["veterinario_id"],
        externo_id=clinica_context["cirujano_id"],
        inicio=inicio,
    )
    assert valido.status_code == 201
    assert valido.json()["estado"] == "PENDIENTE_EXTERNO"
    assert valido.json()["externo_actual_id"] == clinica_context["cirujano_id"]

    sin_token = client.post("/api/turnos", json=payload)
    assert sin_token.status_code == 401


def test_atendido_cirugia_genera_gasto_una_sola_vez(
    client, crear_usuario_clinica, clinica_context, db_session
) -> None:
    usuario, headers = crear_usuario_clinica(Rol.DUENIO)
    _sembrar_horario(client, headers)
    inicio = datetime.combine(_lunes_futuro(), time(10))
    creado = _crear_cirugia(
        client,
        headers,
        paciente_id=clinica_context["paciente_id"],
        veterinario_id=clinica_context["veterinario_id"],
        externo_id=clinica_context["cirujano_id"],
        inicio=inicio,
    )
    confirmado = _confirmar(client, headers, creado.json()["id"], 40000)
    assert confirmado.status_code == 201

    atencion = clinica_service.registrar_atencion(
        db_session,
        clinica_context["paciente_id"],
        AtencionCrear(
            tipo=TipoAtencion.CIRUGIA,
            fecha_hora=inicio,
            veterinario_empleado_id=clinica_context["veterinario_id"],
            cirujano_externo_id=clinica_context["cirujano_id"],
        ),
        created_by=usuario.id,
    )

    atendido = client.post(
        f"/api/turnos/{creado.json()['id']}/atendido",
        headers=headers,
        json={"atencion_id": atencion.id},
    )
    assert atendido.status_code == 200
    cuerpo = atendido.json()
    assert cuerpo["estado"] == "ATENDIDO"
    assert cuerpo["gasto_registrado"] is True
    assert "monto_centavos" not in cuerpo
    assert "costo_acordado_centavos" not in cuerpo

    gastos = cobros_service.listar_gastos_externos(
        db_session, empleado_id=clinica_context["cirujano_id"]
    )
    assert len(gastos.items) == 1
    assert gastos.items[0].monto_centavos == 40000

    repetido = client.post(
        f"/api/turnos/{creado.json()['id']}/atendido",
        headers=headers,
        json={"atencion_id": atencion.id},
    )
    assert repetido.status_code == 409
    gastos_finales = cobros_service.listar_gastos_externos(
        db_session, empleado_id=clinica_context["cirujano_id"]
    )
    assert len(gastos_finales.items) == 1


def test_atendido_cirugia_rechaza_pendiente_y_atencion_invalida(
    client, crear_usuario_clinica, clinica_context, db_session
) -> None:
    usuario, headers = crear_usuario_clinica(Rol.DUENIO)
    _sembrar_horario(client, headers)
    inicio = datetime.combine(_lunes_futuro(), time(10))
    creado = _crear_cirugia(
        client,
        headers,
        paciente_id=clinica_context["paciente_id"],
        veterinario_id=clinica_context["veterinario_id"],
        externo_id=clinica_context["cirujano_id"],
        inicio=inicio,
    )
    turno_id = creado.json()["id"]

    pendiente = client.post(f"/api/turnos/{turno_id}/atendido", headers=headers)
    assert pendiente.status_code == 409

    assert _confirmar(client, headers, turno_id, 40000).status_code == 201
    sin_atencion = client.post(f"/api/turnos/{turno_id}/atendido", headers=headers)
    assert sin_atencion.status_code == 422
    assert sin_atencion.json()["detail"]["codigo"] == "ATENCION_CIRUGIA_INVALIDA"

    consulta = clinica_service.registrar_atencion(
        db_session,
        clinica_context["paciente_id"],
        AtencionCrear(
            tipo=TipoAtencion.CONSULTA,
            fecha_hora=inicio,
            veterinario_empleado_id=clinica_context["veterinario_id"],
        ),
        created_by=usuario.id,
    )
    atencion_no_cirugia = client.post(
        f"/api/turnos/{turno_id}/atendido",
        headers=headers,
        json={"atencion_id": consulta.id},
    )
    assert atencion_no_cirugia.status_code == 422

    otro_externo = _crear_externo_extra(
        db_session,
        nombre="Otro",
        dni="20000010",
        telefono="11 5555-0010",
    )
    cirugia_otro_externo = clinica_service.registrar_atencion(
        db_session,
        clinica_context["paciente_id"],
        AtencionCrear(
            tipo=TipoAtencion.CIRUGIA,
            fecha_hora=inicio,
            veterinario_empleado_id=clinica_context["veterinario_id"],
            cirujano_externo_id=otro_externo,
        ),
        created_by=usuario.id,
    )
    atencion_otro_externo = client.post(
        f"/api/turnos/{turno_id}/atendido",
        headers=headers,
        json={"atencion_id": cirugia_otro_externo.id},
    )
    assert atencion_otro_externo.status_code == 422


def test_cirugia_cancelada_no_genera_gasto(
    client, crear_usuario_clinica, clinica_context, db_session
) -> None:
    _, headers = crear_usuario_clinica(Rol.DUENIO)
    _sembrar_horario(client, headers)
    inicio = datetime.combine(_lunes_futuro(), time(10))
    creado = _crear_cirugia(
        client,
        headers,
        paciente_id=clinica_context["paciente_id"],
        veterinario_id=clinica_context["veterinario_id"],
        externo_id=clinica_context["cirujano_id"],
        inicio=inicio,
    )
    turno_id = creado.json()["id"]
    assert _confirmar(client, headers, turno_id, 40000).status_code == 201

    cancelado = client.post(
        f"/api/turnos/{turno_id}/cancelar",
        headers=headers,
        json={"motivo": "El tutor canceló la cirugía"},
    )
    assert cancelado.status_code == 200
    assert cancelado.json()["estado"] == "CANCELADO"

    atendido = client.post(f"/api/turnos/{turno_id}/atendido", headers=headers)
    assert atendido.status_code == 409

    gastos = cobros_service.listar_gastos_externos(
        db_session, empleado_id=clinica_context["cirujano_id"]
    )
    assert gastos.items == []
