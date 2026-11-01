from app.modules.clinica import service
from app.modules.identidad.permisos import Rol


def test_rectificar_crea_nueva_atencion_y_conserva_la_original(
    client, db_session, clinica_context, crear_usuario_clinica
) -> None:
    _, headers = crear_usuario_clinica(
        Rol.VETERINARIO,
        empleado_id=clinica_context["veterinario_id"],
    )
    paciente_url = f"/api/pacientes/{clinica_context['paciente_id']}/atenciones"
    original_response = client.post(
        paciente_url,
        json={
            "tipo": "CONSULTA",
            "fecha_hora": "2026-11-01T09:00:00-03:00",
            "motivo": "Control",
            "diagnostico": "Diagnóstico inicial",
        },
        headers=headers,
    )
    assert original_response.status_code == 201
    original_id = original_response.json()["id"]

    rectificacion = client.post(
        f"/api/atenciones/{original_id}/rectificar",
        json={
            "tipo": "CONSULTA",
            "fecha_hora": "2026-11-01T09:00:00-03:00",
            "motivo": "Control",
            "diagnostico": "Diagnóstico corregido",
        },
        headers=headers,
    )
    assert rectificacion.status_code == 201
    nueva = rectificacion.json()
    assert nueva["rectifica_a_id"] == original_id
    assert nueva["diagnostico"] == "Diagnóstico corregido"

    anterior = client.get(f"/api/atenciones/{original_id}", headers=headers)
    assert anterior.status_code == 200
    assert anterior.json()["rectificada"] is True
    assert anterior.json()["diagnostico"] == "Diagnóstico inicial"

    historial = client.get(paciente_url, headers=headers)
    assert historial.status_code == 200
    assert {item["id"] for item in historial.json()} == {
        original_id,
        nueva["id"],
    }
    ultima = service.ultima_atencion(
        db_session, clinica_context["paciente_id"]
    )
    assert ultima is not None
    assert ultima.id == nueva["id"]

    assert client.patch(
        f"/api/atenciones/{original_id}", json={}, headers=headers
    ).status_code == 405
    assert client.delete(
        f"/api/atenciones/{original_id}", headers=headers
    ).status_code == 405


def test_rectificar_una_atencion_ya_rectificada_encadena_la_correccion(
    client, clinica_context, crear_usuario_clinica
) -> None:
    _, headers = crear_usuario_clinica(
        Rol.VETERINARIO,
        empleado_id=clinica_context["veterinario_id"],
    )
    primera = client.post(
        f"/api/pacientes/{clinica_context['paciente_id']}/atenciones",
        json={"tipo": "CONSULTA", "diagnostico": "Inicial"},
        headers=headers,
    )
    assert primera.status_code == 201
    segunda = client.post(
        f"/api/atenciones/{primera.json()['id']}/rectificar",
        json={"tipo": "CONSULTA", "diagnostico": "Primera corrección"},
        headers=headers,
    )
    assert segunda.status_code == 201
    tercera = client.post(
        f"/api/atenciones/{segunda.json()['id']}/rectificar",
        json={"tipo": "CONSULTA", "diagnostico": "Segunda corrección"},
        headers=headers,
    )

    assert tercera.status_code == 201
    assert tercera.json()["rectifica_a_id"] == segunda.json()["id"]
