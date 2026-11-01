"""Fixtures aislados para los tests de historia clínica."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core import parametros
from app.modules.clinica.seed import sembrar_parametros
from app.modules.identidad import service as identidad_service
from app.modules.identidad.permisos import Rol
from app.modules.identidad.schemas import UsuarioCrear
from app.modules.padron import schemas as padron_schemas
from app.modules.padron import service as padron_service
from app.modules.padron.seed import sembrar_especies_tamanios_tipo_contacto

PASSWORD_PRUEBA = "clave-de-prueba-segura"


@pytest.fixture(autouse=True)
def _parametros_clinica(db_session: Session) -> Generator[None, None, None]:
    parametros._limpiar_cache()
    sembrar_parametros(db_session)
    yield
    parametros._limpiar_cache()


@pytest.fixture
def clinica_context(db_session: Session) -> dict[str, int]:
    sembrar_especies_tamanios_tipo_contacto(db_session)

    def crear_empleado(
        nombre: str,
        dni: str,
        telefono: str,
        *,
        tipo: str = "INTERNO",
        es_veterinario: bool = True,
    ) -> int:
        empleado = padron_service.crear_empleado(
            db_session,
            padron_schemas.EmpleadoNuevo(
                persona=padron_schemas.PersonaNueva(
                    nombre=nombre,
                    apellido="Clinica",
                    dni=dni,
                    telefonos=[telefono],
                ),
                tipo=tipo,
                es_veterinario=es_veterinario,
            ),
        )
        return empleado.persona_id

    tutor = padron_service.crear_persona(
        db_session,
        padron_schemas.PersonaNueva(
            nombre="Tutor",
            apellido="Paciente",
            dni="20000001",
            telefonos=["11 5555-0001"],
        ),
    )
    especie = next(
        especie
        for especie in padron_service.listar_especies(db_session)
        if especie.nombre == "Perro"
    )
    paciente = padron_service.crear_paciente(
        db_session,
        padron_schemas.PacienteNuevo(
            nombre="Paciente de prueba",
            especie_id=especie.id,
            titular_persona_id=tutor.id,
        ),
    )
    veterinario_id = crear_empleado(
        "Veterinario",
        "20000002",
        "11 5555-0002",
    )
    cirujano_id = crear_empleado(
        "Cirujano",
        "20000003",
        "11 5555-0003",
        tipo="EXTERNO",
    )
    personal_no_veterinario_id = crear_empleado(
        "Recepcionista",
        "20000004",
        "11 5555-0004",
        es_veterinario=False,
    )
    return {
        "paciente_id": paciente.id,
        "veterinario_id": veterinario_id,
        "cirujano_id": cirujano_id,
        "personal_no_veterinario_id": personal_no_veterinario_id,
    }


@pytest.fixture
def crear_usuario_clinica(db_session: Session, client: TestClient):
    cantidad = 0

    def _crear(
        rol: Rol,
        *,
        empleado_id: int | None = None,
    ):
        nonlocal cantidad
        cantidad += 1
        usuario = identidad_service.crear_usuario(
            db_session,
            UsuarioCrear(
                username=f"clinica-{cantidad}",
                password=PASSWORD_PRUEBA,
                rol=rol,
                empleado_id=empleado_id,
            ),
        )
        respuesta = client.post(
            "/api/auth/login",
            json={
                "username": usuario.username,
                "password": PASSWORD_PRUEBA,
            },
        )
        assert respuesta.status_code == 200
        return usuario, {
            "Authorization": f"Bearer {respuesta.json()['access_token']}"
        }

    return _crear
