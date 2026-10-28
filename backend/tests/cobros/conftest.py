from dataclasses import dataclass

import pytest
from sqlalchemy.orm import Session

from app.modules.cobros import seed as cobros_seed
from app.modules.identidad import service as identidad_service
from app.modules.identidad.permisos import Rol
from app.modules.identidad.schemas import UsuarioCrear
from app.modules.padron import service as padron_service
from app.modules.padron.schemas import EmpleadoNuevo, PacienteNuevo, PersonaNueva
from app.modules.padron.seed import sembrar_especies_tamanios_tipo_contacto


@dataclass(frozen=True)
class ReferenciasCobros:
    persona_id: int
    paciente_id: int
    empleado_id: int
    usuario_id: int


@pytest.fixture
def referencias_cobros(db_session: Session) -> ReferenciasCobros:
    sembrar_especies_tamanios_tipo_contacto(db_session)
    cobros_seed.sembrar_medios_pago(db_session)

    persona = padron_service.crear_persona(
        db_session,
        PersonaNueva(nombre="Tutora", apellido="Prueba"),
        migrado=True,
    )
    especie_id = next(
        especie.id
        for especie in padron_service.listar_especies(db_session)
        if especie.nombre == "Perro"
    )
    paciente = padron_service.crear_paciente(
        db_session,
        PacienteNuevo(
            nombre="Firulais",
            especie_id=especie_id,
            titular_persona_id=persona.id,
        ),
    )
    empleado = padron_service.crear_empleado(
        db_session,
        EmpleadoNuevo(
            persona=PersonaNueva(
                nombre="Veterinario",
                apellido="Externo",
                dni="30111223",
                telefonos=["11 5555-0101"],
            ),
            tipo="EXTERNO",
            es_veterinario=True,
        ),
    )
    usuario = identidad_service.crear_usuario(
        db_session,
        UsuarioCrear(
            username="duenio-cobros",
            password="clave-de-prueba-segura",
            rol=Rol.DUENIO,
        ),
    )

    return ReferenciasCobros(
        persona_id=persona.id,
        paciente_id=paciente.id,
        empleado_id=empleado.persona_id,
        usuario_id=usuario.id,
    )
