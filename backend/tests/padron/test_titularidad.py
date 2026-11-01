"""Titularidad múltiple y cambio de titular (T-13, RN-03 y RN-04)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.padron import repository, service


def _crear_persona(
    crear_persona_api,
    usuario,
    persona_payload,
    *,
    dni: str,
    nombre: str,
    apellido: str,
    telefono: str,
) -> int:
    respuesta = crear_persona_api(
        usuario,
        persona_payload(
            nombre=nombre,
            apellido=apellido,
            dni=dni,
            telefonos=[telefono],
        ),
    )
    assert respuesta.status_code == 201, respuesta.text
    return int(respuesta.json()["id"])


def _crear_paciente(
    client: TestClient, auth, usuario, especie_id: int, titular_id: int
) -> int:
    respuesta = client.post(
        "/api/pacientes",
        json={
            "nombre": "Firulais",
            "especie_id": especie_id,
            "titular_persona_id": titular_id,
        },
        headers=auth(usuario),
    )
    assert respuesta.status_code == 201, respuesta.text
    return int(respuesta.json()["id"])


def _agregar(
    client: TestClient,
    auth,
    usuario,
    paciente_id: int,
    persona_id: int,
    **extra: object,
):
    return client.post(
        f"/api/pacientes/{paciente_id}/titulares",
        json={"persona_id": persona_id, **extra},
        headers=auth(usuario),
    )


def _titulares(client: TestClient, auth, usuario, paciente_id: int, **params):
    respuesta = client.get(
        f"/api/pacientes/{paciente_id}/titulares",
        params=params,
        headers=auth(usuario),
    )
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def test_primer_titular_es_principal_y_el_segundo_no(
    client: TestClient,
    auth,
    duenio,
    crear_persona_api,
    persona_payload,
    especie_perro: int,
) -> None:
    ana = _crear_persona(
        crear_persona_api, duenio, persona_payload,
        dni="30111222", nombre="Ana", apellido="Perez", telefono="11 4444-5555",
    )
    beto = _crear_persona(
        crear_persona_api, duenio, persona_payload,
        dni="30999888", nombre="Beto", apellido="Gomez", telefono="11 6666-7777",
    )
    paciente_id = _crear_paciente(client, auth, duenio, especie_perro, ana)

    respuesta = _agregar(client, auth, duenio, paciente_id, beto)

    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["principal"] is False
    assert respuesta.json()["hasta"] is None
    titulares = _titulares(client, auth, duenio, paciente_id)
    assert [titular["persona_id"] for titular in titulares] == [ana, beto]
    assert [titular["principal"] for titular in titulares] == [True, False]


def test_no_se_repite_una_persona_vigente(
    client: TestClient,
    auth,
    duenio,
    crear_persona_api,
    persona_payload,
    especie_perro: int,
) -> None:
    ana = _crear_persona(
        crear_persona_api, duenio, persona_payload,
        dni="30111222", nombre="Ana", apellido="Perez", telefono="11 4444-5555",
    )
    paciente_id = _crear_paciente(client, auth, duenio, especie_perro, ana)

    respuesta = _agregar(client, auth, duenio, paciente_id, ana)

    assert respuesta.status_code == 409


def test_indice_rechaza_duplicado_si_la_validacion_leyo_un_estado_desactualizado(
    db_session: Session,
    client: TestClient,
    auth,
    duenio,
    crear_persona_api,
    persona_payload,
    especie_perro: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ana = _crear_persona(
        crear_persona_api, duenio, persona_payload,
        dni="30111222", nombre="Ana", apellido="Perez", telefono="11 4444-5555",
    )
    beto = _crear_persona(
        crear_persona_api, duenio, persona_payload,
        dni="30999888", nombre="Beto", apellido="Gomez", telefono="11 6666-7777",
    )
    paciente_id = _crear_paciente(client, auth, duenio, especie_perro, ana)
    assert _agregar(client, auth, duenio, paciente_id, beto).status_code == 201

    listar_vigentes = service.repository.titulares_vigentes

    def lectura_desactualizada(db: Session, id_paciente: int):
        return [
            titular
            for titular in listar_vigentes(db, id_paciente)
            if titular.persona_id != beto
        ]

    monkeypatch.setattr(
        service.repository, "titulares_vigentes", lectura_desactualizada
    )

    with pytest.raises(service.TitularidadConflicto, match="ya es titular vigente"):
        service.agregar_titular(db_session, paciente_id, beto)

    db_session.expire_all()
    titulares = listar_vigentes(db_session, paciente_id)
    assert len(titulares) == 2
    assert len({titular.persona_id for titular in titulares}) == 2


def test_no_se_puede_quitar_al_unico_titular(
    client: TestClient,
    auth,
    duenio,
    crear_persona_api,
    persona_payload,
    especie_perro: int,
) -> None:
    ana = _crear_persona(
        crear_persona_api, duenio, persona_payload,
        dni="30111222", nombre="Ana", apellido="Perez", telefono="11 4444-5555",
    )
    paciente_id = _crear_paciente(client, auth, duenio, especie_perro, ana)

    respuesta = client.delete(
        f"/api/pacientes/{paciente_id}/titulares/{ana}",
        headers=auth(duenio),
    )

    assert respuesta.status_code == 409
    assert len(_titulares(client, auth, duenio, paciente_id)) == 1


def test_no_se_puede_quitar_al_principal_sin_designar_otro(
    client: TestClient,
    auth,
    duenio,
    crear_persona_api,
    persona_payload,
    especie_perro: int,
) -> None:
    ana = _crear_persona(
        crear_persona_api, duenio, persona_payload,
        dni="30111222", nombre="Ana", apellido="Perez", telefono="11 4444-5555",
    )
    beto = _crear_persona(
        crear_persona_api, duenio, persona_payload,
        dni="30999888", nombre="Beto", apellido="Gomez", telefono="11 6666-7777",
    )
    paciente_id = _crear_paciente(client, auth, duenio, especie_perro, ana)
    assert _agregar(client, auth, duenio, paciente_id, beto).status_code == 201

    respuesta = client.delete(
        f"/api/pacientes/{paciente_id}/titulares/{ana}",
        headers=auth(duenio),
    )

    assert respuesta.status_code == 409
    assert len(_titulares(client, auth, duenio, paciente_id)) == 2


def test_quitar_secundario_cierra_la_vigencia_y_conserva_el_historial(
    client: TestClient,
    auth,
    duenio,
    crear_persona_api,
    persona_payload,
    especie_perro: int,
) -> None:
    ana = _crear_persona(
        crear_persona_api, duenio, persona_payload,
        dni="30111222", nombre="Ana", apellido="Perez", telefono="11 4444-5555",
    )
    beto = _crear_persona(
        crear_persona_api, duenio, persona_payload,
        dni="30999888", nombre="Beto", apellido="Gomez", telefono="11 6666-7777",
    )
    paciente_id = _crear_paciente(client, auth, duenio, especie_perro, ana)
    assert _agregar(client, auth, duenio, paciente_id, beto).status_code == 201

    respuesta = client.delete(
        f"/api/pacientes/{paciente_id}/titulares/{beto}",
        headers=auth(duenio),
    )

    assert respuesta.status_code == 204
    assert [t["persona_id"] for t in _titulares(client, auth, duenio, paciente_id)] == [ana]
    historial = _titulares(client, auth, duenio, paciente_id, historial=True)
    assert len(historial) == 2
    cerrada = next(t for t in historial if t["persona_id"] == beto)
    assert cerrada["hasta"] is not None

    repetida = client.delete(
        f"/api/pacientes/{paciente_id}/titulares/{beto}",
        headers=auth(duenio),
    )
    assert repetida.status_code == 404


def test_cambiar_principal_deja_uno_solo_sin_sacar_titulares(
    client: TestClient,
    auth,
    duenio,
    crear_persona_api,
    persona_payload,
    especie_perro: int,
) -> None:
    ana = _crear_persona(
        crear_persona_api, duenio, persona_payload,
        dni="30111222", nombre="Ana", apellido="Perez", telefono="11 4444-5555",
    )
    beto = _crear_persona(
        crear_persona_api, duenio, persona_payload,
        dni="30999888", nombre="Beto", apellido="Gomez", telefono="11 6666-7777",
    )
    paciente_id = _crear_paciente(client, auth, duenio, especie_perro, ana)
    assert _agregar(client, auth, duenio, paciente_id, beto).status_code == 201

    respuesta = client.post(
        f"/api/pacientes/{paciente_id}/titular-principal",
        json={"persona_id": beto},
        headers=auth(duenio),
    )

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["principal"] is True
    titulares = _titulares(client, auth, duenio, paciente_id)
    assert len(titulares) == 2
    assert [t["persona_id"] for t in titulares if t["principal"]] == [beto]
    assert [t["persona_id"] for t in titulares if not t["principal"]] == [ana]


@pytest.mark.parametrize("ruta", ["transferencia", "transferir"])
def test_transferencia_conserva_la_mascota_y_el_historial(
    ruta: str,
    client: TestClient,
    auth,
    duenio,
    crear_persona_api,
    persona_payload,
    especie_perro: int,
) -> None:
    ana = _crear_persona(
        crear_persona_api, duenio, persona_payload,
        dni="30111222", nombre="Ana", apellido="Perez", telefono="11 4444-5555",
    )
    beto = _crear_persona(
        crear_persona_api, duenio, persona_payload,
        dni="30999888", nombre="Beto", apellido="Gomez", telefono="11 6666-7777",
    )
    paciente_id = _crear_paciente(client, auth, duenio, especie_perro, ana)

    respuesta = client.post(
        f"/api/pacientes/{paciente_id}/{ruta}",
        json={"persona_id": beto},
        headers=auth(duenio),
    )

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["persona_id"] == beto
    assert respuesta.json()["principal"] is True
    assert client.get(
        f"/api/pacientes/{paciente_id}", headers=auth(duenio)
    ).status_code == 200
    assert [t["persona_id"] for t in _titulares(client, auth, duenio, paciente_id)] == [beto]
    historial = _titulares(client, auth, duenio, paciente_id, historial=True)
    saliente = next(t for t in historial if t["persona_id"] == ana)
    entrante = next(t for t in historial if t["persona_id"] == beto)
    assert saliente["hasta"] is not None
    assert entrante["hasta"] is None


def test_cargo_existente_sigue_a_nombre_del_titular_anterior_tras_transferir(
    client: TestClient,
    auth,
    duenio,
    crear_persona_api,
    persona_payload,
    especie_perro: int,
) -> None:
    ana = _crear_persona(
        crear_persona_api, duenio, persona_payload,
        dni="30111222", nombre="Ana", apellido="Perez", telefono="11 4444-5555",
    )
    beto = _crear_persona(
        crear_persona_api, duenio, persona_payload,
        dni="30999888", nombre="Beto", apellido="Gomez", telefono="11 6666-7777",
    )
    paciente_id = _crear_paciente(client, auth, duenio, especie_perro, ana)
    cargo_creado = client.post(
        "/api/cargos",
        json={
            "persona_id": ana,
            "paciente_id": paciente_id,
            "concepto": "Consulta veterinaria",
            "total_centavos": 12500,
        },
        headers=auth(duenio),
    )
    assert cargo_creado.status_code == 201, cargo_creado.text
    cargo_id = cargo_creado.json()["id"]

    transferencia = client.post(
        f"/api/pacientes/{paciente_id}/transferir",
        json={"persona_id": beto},
        headers=auth(duenio),
    )

    assert transferencia.status_code == 200, transferencia.text
    cargo = client.get(f"/api/cargos/{cargo_id}", headers=auth(duenio))
    assert cargo.status_code == 200, cargo.text
    assert cargo.json()["persona_id"] == ana
    assert cargo.json()["paciente_id"] == paciente_id


def test_transferir_a_un_titular_vigente_es_conflicto(
    client: TestClient,
    auth,
    duenio,
    crear_persona_api,
    persona_payload,
    especie_perro: int,
) -> None:
    ana = _crear_persona(
        crear_persona_api, duenio, persona_payload,
        dni="30111222", nombre="Ana", apellido="Perez", telefono="11 4444-5555",
    )
    beto = _crear_persona(
        crear_persona_api, duenio, persona_payload,
        dni="30999888", nombre="Beto", apellido="Gomez", telefono="11 6666-7777",
    )
    paciente_id = _crear_paciente(client, auth, duenio, especie_perro, ana)
    assert _agregar(client, auth, duenio, paciente_id, beto).status_code == 201

    respuesta = client.post(
        f"/api/pacientes/{paciente_id}/transferencia",
        json={"persona_id": beto, "de_persona_id": ana},
        headers=auth(duenio),
    )

    assert respuesta.status_code == 409


def test_transferencia_que_falla_en_el_medio_no_cierra_al_saliente(
    db_session: Session,
    client: TestClient,
    auth,
    duenio,
    crear_persona_api,
    persona_payload,
    especie_perro: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ana = _crear_persona(
        crear_persona_api, duenio, persona_payload,
        dni="30111222", nombre="Ana", apellido="Perez", telefono="11 4444-5555",
    )
    beto = _crear_persona(
        crear_persona_api, duenio, persona_payload,
        dni="30999888", nombre="Beto", apellido="Gomez", telefono="11 6666-7777",
    )
    paciente_id = _crear_paciente(client, auth, duenio, especie_perro, ana)

    def _falla(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("falla simulada al insertar la nueva titularidad")

    monkeypatch.setattr(service.repository, "crear_titularidad", _falla)

    with pytest.raises(RuntimeError):
        service.transferir_paciente(db_session, paciente_id, beto)

    db_session.expire_all()
    historial = repository.titulares_historial(db_session, paciente_id)
    assert len(historial) == 1
    assert historial[0].persona_id == ana
    assert historial[0].hasta is None


def test_contacto_alternativo_no_puede_ser_principal(
    client: TestClient,
    auth,
    duenio,
    catalogos,
    db_session: Session,
    crear_persona_api,
    persona_payload,
    especie_perro: int,
) -> None:
    tipo_contacto = repository.obtener_tipo_contacto_por_nombre(
        db_session, "CONTACTO ALTERNATIVO"
    )
    assert tipo_contacto is not None
    ana = _crear_persona(
        crear_persona_api, duenio, persona_payload,
        dni="30111222", nombre="Ana", apellido="Perez", telefono="11 4444-5555",
    )
    contacto = _crear_persona(
        crear_persona_api, duenio, persona_payload,
        dni="30777444", nombre="Carla", apellido="Sosa", telefono="11 2222-3333",
    )
    paciente_id = _crear_paciente(client, auth, duenio, especie_perro, ana)

    alta = _agregar(
        client, auth, duenio, paciente_id, contacto,
        tipo_contacto_id=tipo_contacto.id,
    )
    cambio = client.post(
        f"/api/pacientes/{paciente_id}/titular-principal",
        json={"persona_id": contacto},
        headers=auth(duenio),
    )

    assert alta.status_code == 201, alta.text
    assert alta.json()["tipo"] == "CONTACTO ALTERNATIVO"
    assert alta.json()["principal"] is False
    assert cambio.status_code == 422


def test_veterinario_lee_pero_no_modifica_titulares(
    client: TestClient,
    auth,
    duenio,
    veterinario,
    crear_persona_api,
    persona_payload,
    especie_perro: int,
) -> None:
    ana = _crear_persona(
        crear_persona_api, duenio, persona_payload,
        dni="30111222", nombre="Ana", apellido="Perez", telefono="11 4444-5555",
    )
    beto = _crear_persona(
        crear_persona_api, duenio, persona_payload,
        dni="30999888", nombre="Beto", apellido="Gomez", telefono="11 6666-7777",
    )
    paciente_id = _crear_paciente(client, auth, duenio, especie_perro, ana)

    assert _titulares(client, auth, veterinario, paciente_id)[0]["persona_id"] == ana
    assert _agregar(client, auth, veterinario, paciente_id, beto).status_code == 403
    assert client.post(
        f"/api/pacientes/{paciente_id}/transferencia",
        json={"persona_id": beto},
        headers=auth(veterinario),
    ).status_code == 403
