from sqlalchemy import inspect

from app.modules.identidad.permisos import Rol
from app.modules.padron import service as padron_service


def _estudio(veterinario_id: int, **cambios: object) -> dict[str, object]:
    datos: dict[str, object] = {
        "tipo": "RADIOGRAFIA",
        "fecha": "2026-11-01",
        "descripcion": "Placa de tórax",
        "realizado_por_empleado_id": veterinario_id,
    }
    datos.update(cambios)
    return datos


def test_registrar_estudio_sin_archivo_no_crea_cargo(
    client, clinica_context, crear_usuario_clinica
) -> None:
    _, headers = crear_usuario_clinica(Rol.DUENIO)
    paciente_id = clinica_context["paciente_id"]

    respuesta = client.post(
        f"/api/pacientes/{paciente_id}/estudios",
        json=_estudio(clinica_context["veterinario_id"]),
        headers=headers,
    )

    assert respuesta.status_code == 201
    estudio = respuesta.json()
    assert estudio["tipo"] == "RADIOGRAFIA"
    assert estudio["cargo_id"] is None
    assert estudio["adjuntos"] == []

    listado = client.get(
        f"/api/pacientes/{paciente_id}/estudios",
        headers=headers,
    )
    assert listado.status_code == 200
    assert [item["id"] for item in listado.json()] == [estudio["id"]]


def test_costo_crea_cargo_al_titular_principal_y_guarda_solo_su_id(
    client, clinica_context, crear_usuario_clinica, db_session
) -> None:
    usuario, headers = crear_usuario_clinica(Rol.DUENIO)
    paciente_id = clinica_context["paciente_id"]
    titular_principal = next(
        titular
        for titular in padron_service.titulares_vigentes(db_session, paciente_id)
        if titular.principal
    )

    respuesta = client.post(
        f"/api/pacientes/{paciente_id}/estudios",
        json=_estudio(
            clinica_context["veterinario_id"],
            costo_centavos=1_500_000,
        ),
        headers=headers,
    )

    assert respuesta.status_code == 201
    estudio = respuesta.json()
    assert estudio["cargo_id"] is not None
    assert "costo_centavos" not in estudio

    cargo = client.get(f"/api/cargos/{estudio['cargo_id']}", headers=headers)
    assert cargo.status_code == 200
    assert cargo.json()["persona_id"] == titular_principal.persona_id
    assert cargo.json()["total_inicial"] == 1_500_000
    assert cargo.json()["referencia_tipo"] == "ESTUDIO"
    assert cargo.json()["referencia_id"] == estudio["id"]
    assert cargo.json()["creado_por"] == usuario.id

    columnas = {
        columna["name"] for columna in inspect(db_session.get_bind()).get_columns("estudio")
    }
    assert not columnas.intersection(
        {"costo", "costo_centavos", "monto", "precio", "total", "saldo"}
    )


def test_solo_se_acepta_un_empleado_veterinario(
    client, clinica_context, crear_usuario_clinica
) -> None:
    _, headers = crear_usuario_clinica(Rol.DUENIO)

    respuesta = client.post(
        f"/api/pacientes/{clinica_context['paciente_id']}/estudios",
        json=_estudio(clinica_context["personal_no_veterinario_id"]),
        headers=headers,
    )

    assert respuesta.status_code == 422


def test_paciente_inexistente_no_registra_estudio(
    client, clinica_context, crear_usuario_clinica
) -> None:
    _, headers = crear_usuario_clinica(Rol.DUENIO)

    respuesta = client.post(
        "/api/pacientes/99999/estudios",
        json=_estudio(clinica_context["veterinario_id"]),
        headers=headers,
    )

    assert respuesta.status_code == 404


def test_rol_personal_solo_puede_listar_estudios(
    client, clinica_context, crear_usuario_clinica
) -> None:
    paciente_id = clinica_context["paciente_id"]
    _, headers_duenio = crear_usuario_clinica(Rol.DUENIO)
    _, headers_personal = crear_usuario_clinica(Rol.PERSONAL)
    path = f"/api/pacientes/{paciente_id}/estudios"
    payload = _estudio(clinica_context["veterinario_id"])

    assert client.post(path, json=payload, headers=headers_duenio).status_code == 201
    assert client.get(path, headers=headers_personal).status_code == 200
    assert client.post(path, json=payload, headers=headers_personal).status_code == 403
    assert client.get(path).status_code == 401
    assert client.post(path, json=payload).status_code == 401
