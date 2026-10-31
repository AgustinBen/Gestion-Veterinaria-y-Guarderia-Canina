"""Fixtures de integración para el módulo guardería."""

from collections.abc import Callable, Generator
from dataclasses import dataclass
from datetime import date

import pytest
from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from app.core import parametros
from app.core.base import Base
from app.core.config import get_settings
from app.core.parametros import set_param
from app.modules.cobros import seed as cobros_seed
from app.modules.guarderia.franjas import Franja
from app.modules.guarderia.models import EstadoReserva, Ocupacion, Reserva
from app.modules.guarderia.seed import (
    CUPO_MAXIMO_INICIAL,
    PLAZAS_EMERGENCIA_INICIAL,
)
from app.modules.identidad import security
from app.modules.identidad import service as identidad_service
from app.modules.identidad.permisos import Rol
from app.modules.identidad.schemas import UsuarioCrear, UsuarioPublico
from app.modules.padron import service as padron_service
from app.modules.padron.schemas import PacienteNuevo, PersonaNueva
from app.modules.padron.seed import sembrar_especies_tamanios_tipo_contacto


@dataclass(frozen=True)
class DatosReserva:
    tutor_persona_id: int
    otro_tutor_persona_id: int
    paciente_ids: list[int]


@pytest.fixture(autouse=True)
def limpiar_cache_cupo(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    parametros._limpiar_cache()
    monkeypatch.setattr(
        get_settings(),
        "secret_key",
        "clave-de-pruebas-de-guarderia-con-mas-de-32-bytes",
    )
    yield
    parametros._limpiar_cache()


@pytest.fixture
def sembrar_cupo(db_session: Session) -> None:
    set_param(
        db_session,
        "guarderia.cupo_maximo",
        CUPO_MAXIMO_INICIAL,
        "int",
        modulo="guarderia",
    )
    set_param(
        db_session,
        "guarderia.plazas_emergencia",
        PLAZAS_EMERGENCIA_INICIAL,
        "int",
        modulo="guarderia",
    )


@pytest.fixture
def crear_pacientes(db_session: Session) -> Callable:
    def _crear(
        datos: list[tuple[str, str | None]],
    ) -> list[int]:
        pacientes: list[int] = []
        especies: dict[str, int] = {}
        tamanios: dict[str, int] = {}
        tabla_especie = Base.metadata.tables["especie"]
        tabla_tamanio = Base.metadata.tables["tamanio"]
        tabla_paciente = Base.metadata.tables["paciente"]

        for especie, tamanio in datos:
            if especie not in especies:
                existente = db_session.execute(
                    select(tabla_especie.c.id).where(
                        tabla_especie.c.nombre == especie
                    )
                ).scalar_one_or_none()
                if existente is None:
                    resultado = db_session.execute(
                        insert(tabla_especie).values(nombre=especie)
                    )
                    existente = resultado.inserted_primary_key[0]
                especies[especie] = existente

            tamanio_id = None
            if tamanio is not None:
                if tamanio not in tamanios:
                    existente = db_session.execute(
                        select(tabla_tamanio.c.id).where(
                            tabla_tamanio.c.nombre == tamanio
                        )
                    ).scalar_one_or_none()
                    if existente is None:
                        resultado = db_session.execute(
                            insert(tabla_tamanio).values(nombre=tamanio)
                        )
                        existente = resultado.inserted_primary_key[0]
                    tamanios[tamanio] = existente
                tamanio_id = tamanios[tamanio]

            resultado = db_session.execute(
                insert(tabla_paciente).values(
                    nombre=f"Paciente {len(pacientes)}",
                    especie_id=especies[especie],
                    tamanio_id=tamanio_id,
                )
            )
            pacientes.append(resultado.inserted_primary_key[0])
        db_session.flush()
        return pacientes

    return _crear


@pytest.fixture
def crear_usuario(db_session: Session) -> Callable:
    def _crear(rol: Rol = Rol.DUENIO) -> UsuarioPublico:
        return identidad_service.crear_usuario(
            db_session,
            UsuarioCrear(
                username=f"guarderia-{rol.value.lower()}",
                password="clave-segura-guarderia",
                rol=rol,
            ),
        )

    return _crear


@pytest.fixture
def crear_datos_reserva(db_session: Session) -> Callable:
    def _crear(cantidad_pacientes: int = 1) -> DatosReserva:
        sembrar_especies_tamanios_tipo_contacto(db_session)
        cobros_seed.sembrar_medios_pago(db_session)

        tutor = padron_service.crear_persona(
            db_session,
            PersonaNueva(nombre="Tutora", apellido="Reserva"),
            migrado=True,
        )
        otro_tutor = padron_service.crear_persona(
            db_session,
            PersonaNueva(nombre="Otro", apellido="Tutor"),
            migrado=True,
        )
        especie_perro = next(
            especie
            for especie in padron_service.listar_especies(db_session)
            if especie.nombre == "Perro"
        )
        paciente_ids = [
            padron_service.crear_paciente(
                db_session,
                PacienteNuevo(
                    nombre=f"Paciente reserva {indice}",
                    especie_id=especie_perro.id,
                    titular_persona_id=tutor.id,
                ),
            ).id
            for indice in range(cantidad_pacientes)
        ]
        db_session.commit()
        return DatosReserva(
            tutor_persona_id=tutor.id,
            otro_tutor_persona_id=otro_tutor.id,
            paciente_ids=paciente_ids,
        )

    return _crear


@pytest.fixture
def token_guarderia() -> Callable:
    def _crear(usuario: UsuarioPublico) -> dict[str, str]:
        token = security.crear_token(usuario.id, usuario.rol)
        return {"Authorization": f"Bearer {token}"}

    return _crear


@pytest.fixture
def crear_ocupaciones(db_session: Session) -> Callable:
    def _crear(
        paciente_ids: list[int],
        fecha: date,
        franja: Franja,
        usuario_id: int,
        estado: EstadoReserva = EstadoReserva.CONFIRMADA,
    ) -> None:
        tabla_persona = Base.metadata.tables["persona"]
        resultado = db_session.execute(
            insert(tabla_persona).values(nombre="Tutor", apellido="Prueba")
        )
        tutor_id = resultado.inserted_primary_key[0]
        reserva = Reserva(
            tutor_persona_id=tutor_id,
            desde_fecha=fecha,
            desde_franja=franja,
            hasta_fecha=fecha,
            hasta_franja=franja,
            estado=estado,
            creado_por=usuario_id,
        )
        db_session.add(reserva)
        db_session.flush()
        db_session.add_all(
            [
                Ocupacion(
                    fecha=fecha,
                    franja=franja,
                    reserva_id=reserva.id,
                    paciente_id=paciente_id,
                )
                for paciente_id in paciente_ids
            ]
        )
        db_session.flush()

    return _crear
