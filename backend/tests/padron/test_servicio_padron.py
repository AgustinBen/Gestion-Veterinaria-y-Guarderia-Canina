"""Tests del contrato público de padron.service."""

from __future__ import annotations

from datetime import date
from inspect import Signature, signature

from sqlalchemy import event

from app.modules.padron import models, repository, schemas, service


def test_contrato_publico_expone_las_funciones_y_esta_tipado() -> None:
    for nombre in (
        "buscar_personas",
        "buscar_pacientes",
        "obtener_persona",
        "obtener_paciente",
        "obtener_pacientes",
        "titulares_vigentes",
        "obtener_empleado",
        "crear_persona",
    ):
        funcion = getattr(service, nombre)
        assert callable(funcion)
        firma: Signature = signature(funcion)
        assert firma.return_annotation is not Signature.empty


def test_buscar_y_obtener_persona(db_session, persona_payload) -> None:
    creada = service.crear_persona(
        db_session, schemas.PersonaNueva(**persona_payload())
    )

    encontradas = service.buscar_personas(db_session, "Pere", limite=20)
    detalle = service.obtener_persona(db_session, creada.id)

    assert [persona.id for persona in encontradas] == [creada.id]
    assert detalle is not None
    assert detalle.apellido == "Perez"


def test_crear_paciente_y_titulares_principal_primero(
    db_session, persona_payload, catalogos
) -> None:
    titular_principal = service.crear_persona(
        db_session, schemas.PersonaNueva(**persona_payload())
    )
    segundo_titular = service.crear_persona(
        db_session,
        schemas.PersonaNueva(
            nombre="Beto",
            apellido="Gomez",
            dni="30999888",
            telefonos=["11 6666-7777"],
        ),
    )
    especie = service.listar_especies(db_session)[0]
    paciente = service.crear_paciente(
        db_session,
        schemas.PacienteNuevo(
            nombre="Firulais",
            especie_id=especie.id,
            fecha_nacimiento_aprox=date(2000, 1, 1),
            titular_persona_id=titular_principal.id,
        ),
    )
    tipo_titular = repository.obtener_tipo_contacto_por_nombre(
        db_session, "TITULAR"
    )
    assert tipo_titular is not None
    repository.crear_titularidad(
        db_session,
        models.Titularidad(
            paciente_id=paciente.id,
            persona_id=segundo_titular.id,
            tipo_contacto_id=tipo_titular.id,
            principal=False,
            desde=date.today(),
        ),
    )
    db_session.commit()

    titulares = service.titulares_vigentes(db_session, paciente.id)
    detalle = service.obtener_paciente(db_session, paciente.id)

    assert [titular.persona_id for titular in titulares] == [
        titular_principal.id,
        segundo_titular.id,
    ]
    assert titulares[0].principal is True
    assert detalle is not None
    assert detalle.especie_id == especie.id
    assert detalle.edad_anios is not None
    assert "factor_cupo" not in detalle.model_dump()
    assert [p.id for p in service.pacientes_de_persona(db_session, titular_principal.id)] == [
        paciente.id
    ]


def test_obtener_empleado(db_session) -> None:
    creado = service.crear_empleado(
        db_session,
        schemas.EmpleadoNuevo(
            persona=schemas.PersonaNueva(
                nombre="Carlos",
                apellido="Vet",
                dni="31111222",
                telefonos=["11 4444-5555"],
            ),
            es_veterinario=True,
            especialidad="Clínica",
        ),
    )

    detalle = service.obtener_empleado(db_session, creado.persona_id)

    assert detalle is not None
    assert detalle.es_veterinario is True
    assert detalle.especialidad == "Clínica"


def test_obtener_persona_y_paciente_inexistentes_devuelven_none(db_session) -> None:
    assert service.obtener_persona(db_session, 999) is None
    assert service.obtener_paciente(db_session, 999) is None
    assert service.obtener_empleado(db_session, 999) is None


def test_obtener_pacientes_trae_detalles_en_lote_con_consultas_acotadas(
    db_session,
    persona_payload,
    catalogos,
) -> None:
    tutor = service.crear_persona(
        db_session, schemas.PersonaNueva(**persona_payload())
    )
    especie = service.listar_especies(db_session)[0]
    primero = service.crear_paciente(
        db_session,
        schemas.PacienteNuevo(
            nombre="Primero",
            especie_id=especie.id,
            titular_persona_id=tutor.id,
        ),
    )
    segundo = service.crear_paciente(
        db_session,
        schemas.PacienteNuevo(
            nombre="Segundo",
            especie_id=especie.id,
            titular_persona_id=tutor.id,
        ),
    )

    consultas: list[str] = []
    engine = db_session.get_bind()

    def registrar_consulta(
        _conn,
        _cursor,
        sentencia: str,
        _parametros,
        _contexto,
        _executemany: bool,
    ) -> None:
        consultas.append(sentencia)

    event.listen(engine, "before_cursor_execute", registrar_consulta)
    try:
        detalles = service.obtener_pacientes(
            db_session, [segundo.id, primero.id, 999999]
        )
        vacio = service.obtener_pacientes(db_session, [])
    finally:
        event.remove(engine, "before_cursor_execute", registrar_consulta)

    assert list(detalles) == [primero.id, segundo.id]
    assert detalles[primero.id].nombre == "Primero"
    assert detalles[segundo.id].nombre == "Segundo"
    assert vacio == {}
    assert len(consultas) <= 4


def test_obtener_personas_resumen_trae_telefonos_en_lote(
    db_session, persona_payload
) -> None:
    primera = service.crear_persona(
        db_session, schemas.PersonaNueva(**persona_payload())
    )
    segunda = service.crear_persona(
        db_session,
        schemas.PersonaNueva(
            nombre="Beto",
            apellido="Gomez",
            dni="30999888",
            telefonos=["11 6666-7777", "11 6666-8888"],
        ),
    )

    resumen = service.obtener_personas_resumen(
        db_session, [segunda.id, primera.id, 999999]
    )

    assert list(resumen) == [primera.id, segunda.id]
    assert resumen[primera.id].telefonos == ["1144445555"]
    assert resumen[segunda.id].telefonos == ["1166667777", "1166668888"]
