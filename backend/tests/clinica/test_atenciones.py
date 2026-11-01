import pytest

from app.modules.clinica import service
from app.modules.identidad.permisos import Rol


def _consulta(**cambios: object) -> dict[str, object]:
    datos: dict[str, object] = {
        "tipo": "CONSULTA",
        "fecha_hora": "2026-11-01T10:00:00-03:00",
        "motivo": "Control",
        "diagnostico": "Buen estado general",
        "tratamiento": "Continuar controles",
    }
    datos.update(cambios)
    return datos


def test_registrar_consulta_y_listarla(
    client, clinica_context, crear_usuario_clinica
) -> None:
    veterinario, headers = crear_usuario_clinica(
        Rol.VETERINARIO,
        empleado_id=clinica_context["veterinario_id"],
    )
    respuesta = client.post(
        f"/api/pacientes/{clinica_context['paciente_id']}/atenciones",
        json=_consulta(),
        headers=headers,
    )

    assert respuesta.status_code == 201
    atencion = respuesta.json()
    assert atencion["motivo"] == "Control"
    assert atencion["diagnostico"] == "Buen estado general"
    assert atencion["tratamiento"] == "Continuar controles"
    assert atencion["veterinario_empleado_id"] == clinica_context["veterinario_id"]
    assert atencion["created_by"] == veterinario.id
    assert atencion["fecha_hora"].startswith("2026-11-01T10:00:00")

    linea = client.get(
        f"/api/pacientes/{clinica_context['paciente_id']}/atenciones",
        headers=headers,
    )
    assert linea.status_code == 200
    assert linea.json()[0]["id"] == atencion["id"]
    assert linea.json()[0]["veterinario_nombre"] == "Veterinario Clinica"


def test_fecha_hora_se_completa_con_reloj_del_servidor(
    client, clinica_context, crear_usuario_clinica
) -> None:
    _, headers = crear_usuario_clinica(
        Rol.DUENIO,
        empleado_id=clinica_context["veterinario_id"],
    )
    respuesta = client.post(
        f"/api/pacientes/{clinica_context['paciente_id']}/atenciones",
        json={"tipo": "CONSULTA"},
        headers=headers,
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["fecha_hora"]


def test_paciente_inexistente_devuelve_404(
    client, clinica_context, crear_usuario_clinica
) -> None:
    _, headers = crear_usuario_clinica(Rol.DUENIO)

    respuesta = client.get("/api/pacientes/99999/atenciones", headers=headers)

    assert respuesta.status_code == 404


@pytest.mark.parametrize(
    ("veterinario_id", "esperado"),
    [(99999, 422), (None, 422)],
)
def test_veterinario_inexistente_o_no_resoluble_es_rechazado(
    client,
    clinica_context,
    crear_usuario_clinica,
    veterinario_id: int | None,
    esperado: int,
) -> None:
    _, headers = crear_usuario_clinica(Rol.DUENIO)
    datos = _consulta(veterinario_empleado_id=veterinario_id)
    if veterinario_id is None:
        datos.pop("veterinario_empleado_id")

    respuesta = client.post(
        f"/api/pacientes/{clinica_context['paciente_id']}/atenciones",
        json=datos,
        headers=headers,
    )

    assert respuesta.status_code == esperado


def test_empleado_no_veterinario_es_rechazado(
    client, clinica_context, crear_usuario_clinica
) -> None:
    _, headers = crear_usuario_clinica(Rol.DUENIO)

    respuesta = client.post(
        f"/api/pacientes/{clinica_context['paciente_id']}/atenciones",
        json=_consulta(
            veterinario_empleado_id=clinica_context[
                "personal_no_veterinario_id"
            ]
        ),
        headers=headers,
    )

    assert respuesta.status_code == 422


def test_cirugia_exige_un_cirujano_externo(
    client, clinica_context, crear_usuario_clinica
) -> None:
    _, headers = crear_usuario_clinica(
        Rol.VETERINARIO,
        empleado_id=clinica_context["veterinario_id"],
    )
    path = f"/api/pacientes/{clinica_context['paciente_id']}/atenciones"
    base = {"tipo": "CIRUGIA"}

    assert client.post(path, json=base, headers=headers).status_code == 422
    interno = client.post(
        path,
        json={
            **base,
            "cirujano_externo_id": clinica_context["veterinario_id"],
        },
        headers=headers,
    )
    assert interno.status_code == 422
    externo = client.post(
        path,
        json={
            **base,
            "cirujano_externo_id": clinica_context["cirujano_id"],
        },
        headers=headers,
    )
    assert externo.status_code == 201


def test_filtros_de_tipo_fecha_orden_y_paginacion(
    client, clinica_context, crear_usuario_clinica
) -> None:
    _, headers = crear_usuario_clinica(
        Rol.VETERINARIO,
        empleado_id=clinica_context["veterinario_id"],
    )
    for fecha_hora in (
        "2026-10-30T09:00:00-03:00",
        "2026-11-01T09:00:00-03:00",
        "2026-11-01T10:00:00-03:00",
    ):
        respuesta = client.post(
            f"/api/pacientes/{clinica_context['paciente_id']}/atenciones",
            json=_consulta(fecha_hora=fecha_hora),
            headers=headers,
        )
        assert respuesta.status_code == 201

    filtradas = client.get(
        f"/api/pacientes/{clinica_context['paciente_id']}/atenciones",
        params={
            "tipo": "CONSULTA",
            "desde": "2026-11-01",
            "hasta": "2026-11-01",
            "limit": 1,
        },
        headers=headers,
    )
    assert filtradas.status_code == 200
    assert len(filtradas.json()) == 1
    assert filtradas.json()[0]["fecha_hora"].startswith("2026-11-01T10:00:00")

    pagina_dos = client.get(
        f"/api/pacientes/{clinica_context['paciente_id']}/atenciones",
        params={"limit": 1, "offset": 1},
        headers=headers,
    )
    assert pagina_dos.status_code == 200
    assert pagina_dos.json()[0]["fecha_hora"].startswith("2026-11-01T09:00:00")


def test_ultima_atencion_es_none_si_no_hay_historial(
    db_session, clinica_context
) -> None:
    assert service.ultima_atencion(
        db_session, clinica_context["paciente_id"]
    ) is None
