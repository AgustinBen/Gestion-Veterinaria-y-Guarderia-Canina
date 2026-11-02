from app.modules.identidad.permisos import Rol


def test_paciente_sin_turno(client, crear_usuario_clinica, clinica_context) -> None:
    _, headers = crear_usuario_clinica(Rol.DUENIO)
    pid = clinica_context["paciente_id"]
    for path in (
        f"/api/pacientes/{pid}",
        f"/api/pacientes/{pid}/atenciones",
        f"/api/pacientes/{pid}/libreta-vacunas",
        f"/api/pacientes/{pid}/estudios",
        "/api/empleados",
    ):
        respuesta = client.get(path, headers=headers)
        print(path, respuesta.status_code, respuesta.text[:500])
        assert respuesta.status_code == 200
