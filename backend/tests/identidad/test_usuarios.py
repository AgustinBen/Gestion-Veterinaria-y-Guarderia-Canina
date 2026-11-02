"""Tests de listado, alta y modificación de usuarios."""

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.identidad import security
from app.modules.identidad.models import USERNAME_MAX_LENGTH, Usuario
from app.modules.identidad.permisos import Rol
from app.modules.padron import schemas as padron_schemas
from app.modules.padron import service as padron_service
from app.modules.padron.seed import sembrar_parametros_padron


def _contar_usuarios(db: Session) -> int:
    return db.execute(select(func.count()).select_from(Usuario)).scalar_one()


@pytest.fixture(autouse=True)
def _padron_sembrado(db_session: Session) -> None:
    sembrar_parametros_padron(db_session)


def _empleado(dni: str = "30111222", **extra: object) -> dict[str, object]:
    return {
        "nombre": "Ana",
        "apellido": "Paz",
        "dni": dni,
        "telefono": "11 5555-0101",
        **extra,
    }


def _crear_api(
    client,
    auth: dict[str, str],
    username: str,
    password: str,
    rol: Rol = Rol.PERSONAL,
    empleado: dict[str, object] | None = None,
):
    payload: dict[str, object] = {
        "username": username,
        "password": password,
        "rol": rol.value,
    }
    if empleado is None and rol in (Rol.PERSONAL, Rol.VETERINARIO):
        # DNI y teléfono distintos por usuario para no chocar con RN-02 y RN-06.
        indice = sum(ord(c) for c in username)
        empleado = _empleado(
            dni=str(40000000 + indice), telefono=f"11 6000-{indice:04d}"
        )
        empleado["apellido"] = f"Apellido{indice}"
    if empleado is not None:
        payload["empleado"] = empleado
    return client.post("/api/usuarios", headers=auth, json=payload)


def _contar_empleados(db: Session) -> int:
    return len(padron_service.listar_empleados(db))


def test_listar_usuarios_solo_duenio_e_incluye_inactivos(
    client, crear_usuario, auth_de
) -> None:
    actor = crear_usuario("actor", rol=Rol.DUENIO)
    personal = crear_usuario("personal", rol=Rol.PERSONAL)
    vet = crear_usuario("vet", rol=Rol.VETERINARIO)
    crear_usuario("vet_inactivo", rol=Rol.VETERINARIO, activo=False)

    respuesta = client.get("/api/usuarios", headers=auth_de(actor))

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert {usuario["username"] for usuario in datos} == {
        "actor",
        "personal",
        "vet",
        "vet_inactivo",
    }
    assert all(
        "password" not in usuario and "password_hash" not in usuario
        for usuario in datos
    )
    inactivo = next(
        usuario for usuario in datos if usuario["username"] == "vet_inactivo"
    )
    assert inactivo["activo"] is False

    assert (
        client.get("/api/usuarios", headers=auth_de(personal)).status_code == 403
    )
    assert client.get("/api/usuarios", headers=auth_de(vet)).status_code == 403
    assert client.get("/api/usuarios").status_code == 401


@pytest.mark.parametrize(
    ("rol", "es_veterinario", "especialidad"),
    [(Rol.VETERINARIO, True, "Cirugía"), (Rol.PERSONAL, False, None)],
)
def test_crear_cuenta_crea_empleado_interno_y_lo_vincula(
    client,
    duenio,
    auth_de,
    db_session: Session,
    password_prueba,
    rol: Rol,
    es_veterinario: bool,
    especialidad: str | None,
) -> None:
    extra = {"especialidad": "Cirugía"} if rol == Rol.VETERINARIO else {}
    respuesta = _crear_api(
        client,
        auth_de(duenio),
        "  Nueva  ",
        password_prueba,
        rol,
        empleado=_empleado(**extra),
    )

    assert respuesta.status_code == 201
    datos = respuesta.json()
    assert datos["username"] == "nueva"
    assert datos["rol"] == rol.value
    assert datos["activo"] is True
    assert set(datos) == {
        "id",
        "username",
        "rol",
        "activo",
        "empleado_id",
        "creado_en",
    }

    empleado = padron_service.obtener_empleado(db_session, datos["empleado_id"])
    assert empleado is not None
    assert empleado.tipo.value == "INTERNO"
    assert empleado.activo is True
    assert empleado.es_veterinario is es_veterinario
    assert empleado.especialidad == especialidad
    assert (empleado.nombre, empleado.apellido) == ("Ana", "Paz")
    assert empleado.dni == "30111222"

    db_session.expire_all()
    guardado = db_session.get(Usuario, datos["id"])
    assert guardado is not None
    assert guardado.empleado_id == datos["empleado_id"]
    assert guardado.password_hash != password_prueba
    assert security.verificar_password(guardado.password_hash, password_prueba)

    login = client.post(
        "/api/auth/login",
        json={"username": "NUEVA", "password": password_prueba},
    )
    assert login.status_code == 200


def test_personal_ignora_especialidad(
    client, duenio, auth_de, db_session: Session, password_prueba
) -> None:
    respuesta = _crear_api(
        client,
        auth_de(duenio),
        "recepcion",
        password_prueba,
        Rol.PERSONAL,
        empleado=_empleado(especialidad="Cirugía"),
    )

    assert respuesta.status_code == 201
    empleado = padron_service.obtener_empleado(
        db_session, respuesta.json()["empleado_id"]
    )
    assert empleado is not None
    assert empleado.especialidad is None


@pytest.mark.parametrize("rol", [Rol.PERSONAL, Rol.VETERINARIO])
@pytest.mark.parametrize("faltante", ["nombre", "apellido", "dni", "telefono"])
def test_cuenta_exige_datos_obligatorios_del_empleado(
    client, duenio, auth_de, db_session: Session, password_prueba, rol, faltante
) -> None:
    empleado = _empleado()
    del empleado[faltante]
    usuarios = _contar_usuarios(db_session)

    respuesta = _crear_api(
        client, auth_de(duenio), "nueva", password_prueba, rol, empleado=empleado
    )

    assert respuesta.status_code == 422
    assert _contar_usuarios(db_session) == usuarios
    assert _contar_empleados(db_session) == 0


@pytest.mark.parametrize("rol", [Rol.PERSONAL, Rol.VETERINARIO])
def test_cuenta_personal_o_veterinaria_sin_empleado_422(
    client, duenio, auth_de, db_session: Session, password_prueba, rol: Rol
) -> None:
    usuarios = _contar_usuarios(db_session)

    respuesta = client.post(
        "/api/usuarios",
        headers=auth_de(duenio),
        json={
            "username": "sin_empleado",
            "password": password_prueba,
            "rol": rol.value,
        },
    )

    assert respuesta.status_code == 422
    assert _contar_usuarios(db_session) == usuarios


def test_cuenta_duenio_no_lleva_empleado(
    client, duenio, auth_de, db_session: Session, password_prueba
) -> None:
    sin = _crear_api(
        client, auth_de(duenio), "otro_duenio", password_prueba, Rol.DUENIO
    )
    con = _crear_api(
        client,
        auth_de(duenio),
        "duenio_con_empleado",
        password_prueba,
        Rol.DUENIO,
        empleado=_empleado(),
    )

    assert sin.status_code == 201
    assert sin.json()["empleado_id"] is None
    assert con.status_code == 422
    assert _contar_empleados(db_session) == 0


def test_cuenta_con_dni_repetido_409_y_no_crea_nada(
    client, duenio, auth_de, db_session: Session, password_prueba
) -> None:
    headers = auth_de(duenio)
    primera = _crear_api(
        client, headers, "primera", password_prueba, empleado=_empleado()
    )
    usuarios = _contar_usuarios(db_session)
    empleados = _contar_empleados(db_session)

    segunda = _crear_api(
        client,
        headers,
        "segunda",
        password_prueba,
        empleado=_empleado(telefono="11 4444-0000", nombre="Luis", apellido="Gómez"),
    )

    assert primera.status_code == 201
    assert segunda.status_code == 409
    assert segunda.json()["detail"]["codigo"] == "DNI_DUPLICADO"
    assert _contar_usuarios(db_session) == usuarios
    assert _contar_empleados(db_session) == empleados


def test_cuenta_con_telefono_repetido_pide_confirmacion(
    client, duenio, auth_de, db_session: Session, password_prueba
) -> None:
    headers = auth_de(duenio)
    _crear_api(client, headers, "primera", password_prueba, empleado=_empleado())
    otro = _empleado(dni="30999888", nombre="Luis", apellido="Gómez")

    sin_confirmar = _crear_api(
        client, headers, "segunda", password_prueba, empleado=otro
    )
    assert sin_confirmar.status_code == 409
    assert sin_confirmar.json()["detail"]["codigo"] == "POSIBLE_DUPLICADO"
    assert _contar_empleados(db_session) == 1

    confirmado = _crear_api(
        client,
        headers,
        "segunda",
        password_prueba,
        empleado={**otro, "confirmar_duplicado": True},
    )
    assert confirmado.status_code == 201
    assert _contar_empleados(db_session) == 2


def test_username_repetido_no_deja_empleado_huerfano(
    client, duenio, auth_de, db_session: Session, password_prueba
) -> None:
    headers = auth_de(duenio)
    _crear_api(client, headers, "ana", password_prueba, empleado=_empleado())
    empleados = _contar_empleados(db_session)

    repetida = _crear_api(
        client,
        headers,
        "ANA",
        password_prueba,
        empleado=_empleado(dni="30999888", telefono="11 4444-0000"),
    )

    assert repetida.status_code == 409
    assert repetida.json() == {"detail": "El username ya está registrado"}
    assert _contar_empleados(db_session) == empleados


def test_crear_usuario_duplicado_case_insensitive(
    client, duenio, auth_de, db_session: Session, password_prueba
) -> None:
    headers = auth_de(duenio)
    primera = _crear_api(client, headers, "Ana", password_prueba)
    segunda = _crear_api(client, headers, "ANA", password_prueba)

    assert primera.status_code == 201
    assert segunda.status_code == 409
    assert segunda.json() == {"detail": "El username ya está registrado"}
    assert _contar_usuarios(db_session) == 2


@pytest.mark.parametrize("rol", [Rol.PERSONAL, Rol.VETERINARIO])
def test_crear_usuario_rechaza_otros_roles(
    client, crear_usuario, auth_de, password_prueba, rol: Rol
) -> None:
    usuario = crear_usuario(f"user_{rol.value}", rol=rol)

    respuesta = _crear_api(
        client, auth_de(usuario), "nueva", password_prueba
    )

    assert respuesta.status_code == 403


def test_crear_usuario_sin_token_401(client, password_prueba) -> None:
    respuesta = client.post(
        "/api/usuarios",
        json={
            "username": "nueva",
            "password": password_prueba,
            "rol": "PERSONAL",
        },
    )

    assert respuesta.status_code == 401


@pytest.mark.parametrize("username", ["   ", "x" * (USERNAME_MAX_LENGTH + 1)])
def test_crear_usuario_username_invalido_422(
    client, duenio, auth_de, db_session: Session, password_prueba, username: str
) -> None:
    antes = _contar_usuarios(db_session)

    respuesta = _crear_api(
        client, auth_de(duenio), username, password_prueba
    )

    assert respuesta.status_code == 422
    assert _contar_usuarios(db_session) == antes


def test_crear_usuario_rol_invalido_422(
    client, duenio, auth_de, db_session: Session, password_prueba
) -> None:
    antes = _contar_usuarios(db_session)

    respuesta = client.post(
        "/api/usuarios",
        headers=auth_de(duenio),
        json={
            "username": "nueva",
            "password": password_prueba,
            "rol": "ROOT",
        },
    )

    assert respuesta.status_code == 422
    assert _contar_usuarios(db_session) == antes


def test_crear_usuario_password_minima_configurable(
    client,
    duenio,
    auth_de,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    minimo = get_settings().password_min_length + 4
    monkeypatch.setattr(get_settings(), "password_min_length", minimo)
    headers = auth_de(duenio)
    antes = _contar_usuarios(db_session)

    corta = _crear_api(client, headers, "corta", "x" * (minimo - 1))
    en_minimo = _crear_api(client, headers, "en_minimo", "x" * minimo)

    assert corta.status_code == 422
    assert en_minimo.status_code == 201
    assert _contar_usuarios(db_session) == antes + 1


def test_patch_desactiva_y_reactiva(
    client, duenio, crear_usuario, auth_de, token_de, password_prueba
) -> None:
    objetivo = crear_usuario("objetivo", rol=Rol.PERSONAL)
    headers = auth_de(duenio)
    token_objetivo = {"Authorization": f"Bearer {token_de(objetivo)}"}
    ruta = f"/api/usuarios/{objetivo.id}"

    desactivado = client.patch(ruta, headers=headers, json={"activo": False})

    assert desactivado.status_code == 200
    assert desactivado.json()["activo"] is False
    assert (
        client.get("/api/auth/me", headers=token_objetivo).status_code == 401
    )
    assert (
        client.post(
            "/api/auth/login",
            json={"username": "objetivo", "password": password_prueba},
        ).status_code
        == 401
    )

    reactivado = client.patch(ruta, headers=headers, json={"activo": True})

    assert reactivado.status_code == 200
    assert reactivado.json()["activo"] is True
    assert client.get("/api/auth/me", headers=token_objetivo).status_code == 200
    assert (
        client.post(
            "/api/auth/login",
            json={"username": "objetivo", "password": password_prueba},
        ).status_code
        == 200
    )


def test_patch_cambia_password(
    client,
    duenio,
    crear_usuario,
    auth_de,
    db_session: Session,
    password_prueba,
) -> None:
    objetivo = crear_usuario("objetivo", password=password_prueba)
    nueva = f"{password_prueba}-nueva"

    respuesta = client.patch(
        f"/api/usuarios/{objetivo.id}",
        headers=auth_de(duenio),
        json={"password": nueva},
    )

    assert respuesta.status_code == 200
    assert "password" not in respuesta.json()
    assert (
        client.post(
            "/api/auth/login",
            json={"username": "objetivo", "password": password_prueba},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/auth/login",
            json={"username": "objetivo", "password": nueva},
        ).status_code
        == 200
    )

    db_session.expire_all()
    guardado = db_session.get(Usuario, objetivo.id)
    assert guardado is not None
    assert security.verificar_password(guardado.password_hash, nueva)


def test_patch_vincula_usuario_con_empleado_existente(
    client, duenio, crear_usuario, auth_de, db_session: Session
) -> None:
    sembrar_parametros_padron(db_session)
    empleado = padron_service.crear_empleado(
        db_session,
        padron_schemas.EmpleadoNuevo(
            persona=padron_schemas.PersonaNueva(
                nombre="Veterinario",
                apellido="Prueba",
                telefonos=["11 5555-0102"],
            ),
            es_veterinario=True,
        ),
        migrado=True,
    )
    usuario = crear_usuario("veterinario", rol=Rol.VETERINARIO)

    respuesta = client.patch(
        f"/api/usuarios/{usuario.id}",
        headers=auth_de(duenio),
        json={"empleado_id": empleado.persona_id},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["empleado_id"] == empleado.persona_id


def test_patch_rechaza_empleado_inexistente(
    client, duenio, crear_usuario, auth_de
) -> None:
    usuario = crear_usuario("veterinario", rol=Rol.VETERINARIO)

    respuesta = client.patch(
        f"/api/usuarios/{usuario.id}",
        headers=auth_de(duenio),
        json={"empleado_id": 999999},
    )

    assert respuesta.status_code == 422
    assert respuesta.json() == {"detail": "El empleado indicado no existe"}


def test_patch_cambia_rol_y_la_db_manda(
    client, duenio, crear_usuario, auth_de, token_de
) -> None:
    objetivo = crear_usuario("objetivo", rol=Rol.PERSONAL)
    headers_objetivo = {"Authorization": f"Bearer {token_de(objetivo)}"}
    ruta = f"/api/usuarios/{objetivo.id}"
    headers_duenio = auth_de(duenio)

    a_veterinario = client.patch(
        ruta, headers=headers_duenio, json={"rol": "VETERINARIO"}
    )

    assert a_veterinario.status_code == 200
    assert a_veterinario.json()["rol"] == "VETERINARIO"
    me = client.get("/api/auth/me", headers=headers_objetivo)
    assert me.status_code == 200
    assert me.json()["rol"] == "VETERINARIO"
    assert (
        client.get("/api/usuarios", headers=headers_objetivo).status_code == 403
    )

    a_duenio = client.patch(ruta, headers=headers_duenio, json={"rol": "DUENIO"})

    assert a_duenio.status_code == 200
    assert a_duenio.json()["rol"] == "DUENIO"
    assert (
        client.get("/api/usuarios", headers=headers_objetivo).status_code == 200
    )


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"activo": None},
        {"rol": None},
        {"password": None},
        {"username": "otro"},
    ],
)
def test_patch_sin_cambios_validos_422(
    client, duenio, crear_usuario, auth_de, payload: dict[str, object]
) -> None:
    objetivo = crear_usuario("objetivo")

    respuesta = client.patch(
        f"/api/usuarios/{objetivo.id}",
        headers=auth_de(duenio),
        json=payload,
    )

    assert respuesta.status_code == 422


def test_patch_usuario_inexistente_404(client, duenio, auth_de) -> None:
    respuesta = client.patch(
        "/api/usuarios/999999",
        headers=auth_de(duenio),
        json={"activo": False},
    )

    assert respuesta.status_code == 404
    assert respuesta.json() == {"detail": "Usuario no encontrado"}


def test_patch_auto_desactivacion_409(
    client, crear_usuario, auth_de, db_session: Session
) -> None:
    actor = crear_usuario("actor", rol=Rol.DUENIO)
    crear_usuario("otro", rol=Rol.DUENIO)

    respuesta = client.patch(
        f"/api/usuarios/{actor.id}",
        headers=auth_de(actor),
        json={"activo": False},
    )

    assert respuesta.status_code == 409
    db_session.expire_all()
    guardado = db_session.get(Usuario, actor.id)
    assert guardado is not None
    assert guardado.activo is True


def test_patch_ultimo_duenio_no_puede_degradarse(
    client, crear_usuario, auth_de
) -> None:
    actor = crear_usuario("actor", rol=Rol.DUENIO)
    headers = auth_de(actor)

    respuesta = client.patch(
        f"/api/usuarios/{actor.id}",
        headers=headers,
        json={"rol": "PERSONAL"},
    )

    assert respuesta.status_code == 409
    me = client.get("/api/auth/me", headers=headers)
    assert me.json()["rol"] == "DUENIO"


def test_patch_autodemote_con_otro_duenio_ok(
    client, crear_usuario, auth_de
) -> None:
    actor = crear_usuario("actor", rol=Rol.DUENIO)
    otro = crear_usuario("otro", rol=Rol.DUENIO)
    headers = auth_de(actor)

    respuesta = client.patch(
        f"/api/usuarios/{actor.id}",
        headers=headers,
        json={"rol": "PERSONAL"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["rol"] == "PERSONAL"
    assert client.get("/api/usuarios", headers=headers).status_code == 403
    assert client.get("/api/auth/me", headers=auth_de(otro)).json()["rol"] == "DUENIO"


@pytest.mark.parametrize("rol", [Rol.PERSONAL, Rol.VETERINARIO])
def test_patch_no_duenio_403(
    client, crear_usuario, auth_de, rol: Rol
) -> None:
    actor = crear_usuario(f"user_{rol.value}", rol=rol)
    objetivo = crear_usuario("objetivo")
    headers_actor = auth_de(actor)
    headers_objetivo = auth_de(objetivo)

    respuesta = client.patch(
        f"/api/usuarios/{objetivo.id}",
        headers=headers_actor,
        json={"activo": False},
    )

    assert respuesta.status_code == 403
    assert client.get("/api/auth/me", headers=headers_objetivo).status_code == 200


def test_patch_password_corta_422(
    client,
    duenio,
    crear_usuario,
    auth_de,
    monkeypatch: pytest.MonkeyPatch,
    password_prueba,
) -> None:
    minimo = get_settings().password_min_length + 4
    monkeypatch.setattr(get_settings(), "password_min_length", minimo)
    objetivo = crear_usuario("objetivo", password=password_prueba)

    respuesta = client.patch(
        f"/api/usuarios/{objetivo.id}",
        headers=auth_de(duenio),
        json={"password": "x" * (minimo - 1)},
    )

    assert respuesta.status_code == 422
    assert (
        client.post(
            "/api/auth/login",
            json={"username": "objetivo", "password": password_prueba},
        ).status_code
        == 200
    )


def test_patch_desactivar_otro_duenio_ok(
    client, crear_usuario, auth_de
) -> None:
    actor = crear_usuario("actor", rol=Rol.DUENIO)
    objetivo = crear_usuario("objetivo", rol=Rol.DUENIO)
    headers = auth_de(actor)

    respuesta = client.patch(
        f"/api/usuarios/{objetivo.id}",
        headers=headers,
        json={"activo": False},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["activo"] is False
    assert client.get("/api/auth/me", headers=headers).json()["rol"] == "DUENIO"
