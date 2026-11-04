"""El monto de un turno es obligatorio y se registra como cargo del dueño en Cobros."""

from datetime import date, datetime, time, timedelta

from app.modules.cobros import service as cobros_service
from app.modules.identidad.permisos import Rol
from app.modules.padron import service as padron_service


def _lunes_futuro() -> date:
    hoy = date.today()
    return hoy + timedelta(days=(7 - hoy.weekday()) % 7 or 7)


def _preparar(client, crear_usuario_clinica):
    _, duenio = crear_usuario_clinica(Rol.DUENIO)
    client.put(
        "/api/clinica/horarios",
        headers=duenio,
        json=[{"dia_semana": 0, "hora_desde": "09:00", "hora_hasta": "18:00"}],
    )
    return duenio


def _agendar(client, headers, contexto, hora: int, **extra):
    inicio = datetime.combine(_lunes_futuro(), time(hora))
    return client.post(
        "/api/turnos",
        headers=headers,
        json={
            "paciente_id": contexto["paciente_id"],
            "tipo": "CONSULTA",
            "veterinario_empleado_id": contexto["veterinario_id"],
            "inicio": inicio.isoformat(),
            "fin": (inicio + timedelta(minutes=30)).isoformat(),
            **extra,
        },
    )


def test_turno_con_monto_crea_cargo_al_dueno_principal(
    client, db_session, crear_usuario_clinica, clinica_context
) -> None:
    duenio = _preparar(client, crear_usuario_clinica)

    respuesta = _agendar(client, duenio, clinica_context, 10, monto_centavos=1250050)

    assert respuesta.status_code == 201
    turno = respuesta.json()
    assert turno["cargo_id"] is not None
    titular = next(
        t
        for t in padron_service.titulares_vigentes(db_session, clinica_context["paciente_id"])
        if t.principal
    )
    cargo = cobros_service.obtener_cargo_detalle(db_session, turno["cargo_id"])
    assert cargo.persona_id == titular.persona_id
    assert cargo.paciente_id == clinica_context["paciente_id"]
    assert cargo.total_inicial == 1250050
    assert cargo.saldo == 1250050  # deuda calculada: todavía no hay pagos
    assert (cargo.referencia_tipo, cargo.referencia_id) == ("TURNO", turno["id"])

    # El turno guardado conserva el vínculo.
    guardado = client.get(f"/api/turnos/{turno['id']}", headers=duenio).json()
    assert guardado["cargo_id"] == turno["cargo_id"]


def test_turno_sin_monto_se_rechaza(
    client, crear_usuario_clinica, clinica_context
) -> None:
    duenio = _preparar(client, crear_usuario_clinica)

    respuesta = _agendar(client, duenio, clinica_context, 11)

    assert respuesta.status_code == 422
    assert client.get("/api/turnos", headers=duenio).json() == []


def test_monto_invalido_se_rechaza_y_no_crea_turno(
    client, crear_usuario_clinica, clinica_context
) -> None:
    duenio = _preparar(client, crear_usuario_clinica)

    for monto in (0, -100, 10.5, "mil"):
        respuesta = _agendar(client, duenio, clinica_context, 12, monto_centavos=monto)
        assert respuesta.status_code == 422

    assert client.get("/api/turnos", headers=duenio).json() == []


def test_turno_que_falla_no_deja_cargo(
    client, db_session, crear_usuario_clinica, clinica_context
) -> None:
    duenio = _preparar(client, crear_usuario_clinica)
    titular = next(
        t
        for t in padron_service.titulares_vigentes(db_session, clinica_context["paciente_id"])
        if t.principal
    )

    # 20:00 queda fuera del horario: no debe quedar ni turno ni cargo.
    fuera = _agendar(client, duenio, clinica_context, 20, monto_centavos=5000)

    assert fuera.status_code == 422
    assert client.get("/api/turnos", headers=duenio).json() == []
    assert cobros_service.saldo_pendiente(db_session, titular.persona_id) == 0


def test_personal_tambien_puede_agendar_con_monto(
    client, crear_usuario_clinica, clinica_context
) -> None:
    duenio = _preparar(client, crear_usuario_clinica)
    _, personal = crear_usuario_clinica(Rol.PERSONAL)

    respuesta = _agendar(client, personal, clinica_context, 13, monto_centavos=900000)

    assert respuesta.status_code == 201
    assert respuesta.json()["cargo_id"] is not None
    assert client.get("/api/turnos", headers=duenio).status_code == 200
