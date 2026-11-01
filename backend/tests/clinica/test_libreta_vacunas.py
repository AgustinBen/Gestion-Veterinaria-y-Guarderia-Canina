from datetime import date

from app.modules.clinica import service
from app.modules.identidad.permisos import Rol


def _vacuna(
    nombre: str,
    proxima_dosis: str | None,
) -> dict[str, object]:
    return {
        "tipo": "VACUNA",
        "vacuna": {
            "nombre_vacuna": nombre,
            "fecha_aplicacion": "2026-10-01",
            "proxima_dosis": proxima_dosis,
        },
    }


def test_vacuna_aparece_en_libreta_y_estado_se_calcula_con_reloj(
    client, db_session, clinica_context, crear_usuario_clinica
) -> None:
    _, headers = crear_usuario_clinica(
        Rol.VETERINARIO,
        empleado_id=clinica_context["veterinario_id"],
    )
    for nombre, fecha in (
        ("Vacuna próxima", "2026-11-10"),
        ("Vacuna vigente", "2026-12-15"),
        ("Vacuna vencida", "2026-10-20"),
        ("Vacuna sin próxima dosis", None),
    ):
        datos = _vacuna(nombre, fecha)
        respuesta = client.post(
            f"/api/pacientes/{clinica_context['paciente_id']}/atenciones",
            json=datos,
            headers=headers,
        )
        assert respuesta.status_code == 201

    respuesta_libreta = client.get(
        f"/api/pacientes/{clinica_context['paciente_id']}/libreta-vacunas",
        headers=headers,
    )
    assert respuesta_libreta.status_code == 200
    assert len(respuesta_libreta.json()) == 4
    assert respuesta_libreta.json()[0]["nombre_vacuna"] == "Vacuna sin próxima dosis"

    items = service.libreta_vacunas(
        db_session,
        clinica_context["paciente_id"],
        hoy=date(2026, 11, 1),
    )
    estados = {item.nombre_vacuna: item.estado.value for item in items}
    assert estados == {
        "Vacuna próxima": "POR_VENCER",
        "Vacuna vigente": "VIGENTE",
        "Vacuna vencida": "VENCIDA",
        "Vacuna sin próxima dosis": "VIGENTE",
    }


def test_cambiar_parametro_modifica_aviso_vacunal(
    db_session, clinica_context, crear_usuario_clinica
) -> None:
    from app.core import parametros
    from app.modules.clinica.schemas import AtencionCrear

    parametros.set_param(
        db_session,
        "clinica.dias_aviso_vacuna",
        5,
        "int",
        modulo="clinica",
    )
    usuario, _ = crear_usuario_clinica(Rol.DUENIO)
    datos = AtencionCrear.model_validate(
        {
            "tipo": "VACUNA",
            "veterinario_empleado_id": clinica_context["veterinario_id"],
            "vacuna": {
                "nombre_vacuna": "Parvo",
                "fecha_aplicacion": "2026-10-01",
                "proxima_dosis": "2026-11-10",
            },
        }
    )
    service.registrar_atencion(
        db_session,
        clinica_context["paciente_id"],
        datos,
        created_by=usuario.id,
    )

    items = service.libreta_vacunas(
        db_session,
        clinica_context["paciente_id"],
        hoy=date(2026, 11, 1),
    )

    assert items[0].estado.value == "VIGENTE"
