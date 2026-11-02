"""El veterinario solo ve y atiende sus turnos; no agenda ni reprograma."""

from datetime import date, datetime, time, timedelta

from app.modules.identidad.permisos import Rol
from app.modules.padron import schemas as padron_schemas
from app.modules.padron import service as padron_service


def _lunes_futuro() -> date:
    hoy = date.today()
    return hoy + timedelta(days=(7 - hoy.weekday()) % 7 or 7)


def _crear_turno(client, headers, paciente_id, veterinario_id, hora: int):
    inicio = datetime.combine(_lunes_futuro(), time(hora))
    return client.post(
        "/api/turnos",
        headers=headers,
        json={
            "paciente_id": paciente_id,
            "tipo": "CONSULTA",
            "veterinario_empleado_id": veterinario_id,
            "inicio": inicio.isoformat(),
            "fin": (inicio + timedelta(minutes=30)).isoformat(),
        },
    )


def _otro_veterinario(db_session) -> int:
    empleado = padron_service.crear_empleado(
        db_session,
        padron_schemas.EmpleadoNuevo(
            persona=padron_schemas.PersonaNueva(
                nombre="Otra",
                apellido="Veterinaria",
                dni="29888777",
                telefonos=["11 4000-0001"],
            ),
            es_veterinario=True,
        ),
    )
    return empleado.persona_id


def _escenario(client, db_session, crear_usuario_clinica, clinica_context):
    _, duenio = crear_usuario_clinica(Rol.DUENIO)
    _, personal = crear_usuario_clinica(Rol.PERSONAL)
    propio_id = clinica_context["veterinario_id"]
    ajeno_id = _otro_veterinario(db_session)
    _, veterinario = crear_usuario_clinica(Rol.VETERINARIO, empleado_id=propio_id)
    client.put(
        "/api/clinica/horarios",
        headers=duenio,
        json=[{"dia_semana": 0, "hora_desde": "09:00", "hora_hasta": "18:00"}],
    )
    paciente = clinica_context["paciente_id"]
    propio = _crear_turno(client, personal, paciente, propio_id, 10).json()
    ajeno = _crear_turno(client, personal, paciente, ajeno_id, 11).json()
    return duenio, personal, veterinario, propio, ajeno


def test_veterinario_solo_lista_sus_turnos(
    client, db_session, crear_usuario_clinica, clinica_context
) -> None:
    duenio, personal, veterinario, propio, ajeno = _escenario(
        client, db_session, crear_usuario_clinica, clinica_context
    )

    ids = lambda h, **p: {  # noqa: E731
        t["id"] for t in client.get("/api/turnos", headers=h, params=p).json()
    }
    assert ids(veterinario) == {propio["id"]}
    # El filtro del pedido no puede ampliar lo que ve el veterinario.
    assert ids(veterinario, veterinario_id=ajeno["veterinario_empleado_id"]) == {
        propio["id"]
    }
    assert ids(personal) == {propio["id"], ajeno["id"]}
    assert ids(duenio) == {propio["id"], ajeno["id"]}


def test_veterinario_no_accede_al_detalle_de_turnos_ajenos(
    client, db_session, crear_usuario_clinica, clinica_context
) -> None:
    _, _, veterinario, propio, ajeno = _escenario(
        client, db_session, crear_usuario_clinica, clinica_context
    )

    assert client.get(f"/api/turnos/{propio['id']}", headers=veterinario).status_code == 200
    assert client.get(f"/api/turnos/{ajeno['id']}", headers=veterinario).status_code == 404
    assert (
        client.post(f"/api/turnos/{ajeno['id']}/ausente", headers=veterinario).status_code
        == 404
    )
    assert (
        client.post(f"/api/turnos/{ajeno['id']}/atendido", headers=veterinario).status_code
        == 404
    )
    assert (
        client.get(f"/api/turnos/{ajeno['id']}/externo", headers=veterinario).status_code
        == 404
    )


def test_agenda_del_veterinario_solo_incluye_sus_turnos(
    client, db_session, crear_usuario_clinica, clinica_context
) -> None:
    _, personal, veterinario, propio, ajeno = _escenario(
        client, db_session, crear_usuario_clinica, clinica_context
    )
    params = {"desde": _lunes_futuro().isoformat(), "hasta": _lunes_futuro().isoformat()}

    def turnos_de(headers):
        dias = client.get("/api/clinica/agenda", headers=headers, params=params).json()
        return {t["id"] for dia in dias for t in dia["turnos"]}

    assert turnos_de(veterinario) == {propio["id"]}
    assert turnos_de(personal) == {propio["id"], ajeno["id"]}


def test_veterinario_no_agenda_reprograma_ni_cancela(
    client, db_session, crear_usuario_clinica, clinica_context
) -> None:
    _, _, veterinario, propio, _ = _escenario(
        client, db_session, crear_usuario_clinica, clinica_context
    )

    nuevo = _crear_turno(
        client, veterinario, clinica_context["paciente_id"], propio["veterinario_empleado_id"], 15
    )
    reprogramar = client.patch(
        f"/api/turnos/{propio['id']}",
        headers=veterinario,
        json={"inicio": propio["inicio"], "fin": propio["fin"]},
    )
    cancelar = client.post(
        f"/api/turnos/{propio['id']}/cancelar",
        headers=veterinario,
        json={"motivo": "prueba"},
    )

    assert nuevo.status_code == 403
    assert reprogramar.status_code == 403
    assert cancelar.status_code == 403


def test_veterinario_atiende_su_turno_y_personal_no_lo_marca_atendido(
    client, db_session, crear_usuario_clinica, clinica_context
) -> None:
    _, personal, veterinario, propio, ajeno = _escenario(
        client, db_session, crear_usuario_clinica, clinica_context
    )

    assert (
        client.post(f"/api/turnos/{propio['id']}/atendido", headers=personal).status_code
        == 403
    )
    ausente = client.post(f"/api/turnos/{propio['id']}/ausente", headers=veterinario)
    assert ausente.status_code == 200
    assert ausente.json()["estado"] == "AUSENTE"


def test_veterinario_sin_empleado_vinculado_no_ve_turnos(
    client, db_session, crear_usuario_clinica, clinica_context
) -> None:
    _, _, _, propio, _ = _escenario(
        client, db_session, crear_usuario_clinica, clinica_context
    )
    _, sin_empleado = crear_usuario_clinica(Rol.VETERINARIO)

    assert client.get("/api/turnos", headers=sin_empleado).json() == []
    assert client.get(f"/api/turnos/{propio['id']}", headers=sin_empleado).status_code == 404
