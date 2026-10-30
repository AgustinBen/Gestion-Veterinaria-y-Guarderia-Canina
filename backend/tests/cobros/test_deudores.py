from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter

from fastapi.testclient import TestClient

from app.modules.cobros import models, service
from app.modules.identidad import service as identidad_service
from app.modules.identidad.permisos import Rol
from app.modules.identidad.schemas import UsuarioCrear
from app.modules.padron import service as padron_service
from app.modules.padron.schemas import PersonaNueva


def _auth_token(
    client: TestClient, username: str, password: str = "clave-de-prueba-segura"
) -> dict[str, str]:
    respuesta = client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )
    assert respuesta.status_code == 200
    return {"Authorization": f"Bearer {respuesta.json()['access_token']}"}


def _persona(
    db_session, nombre: str, apellido: str, *, confirmar_duplicado: bool = False
):
    return padron_service.crear_persona(
        db_session,
        PersonaNueva(
            nombre=nombre,
            apellido=apellido,
            confirmar_duplicado=confirmar_duplicado,
        ),
        migrado=True,
    )


def _cargo(
    db_session,
    persona_id: int,
    usuario_id: int,
    total: int,
    *,
    origen: models.OrigenCargo = models.OrigenCargo.NORMAL,
    fecha: int = 1,
) -> models.Cargo:
    cargo = models.Cargo(
        persona_id=persona_id,
        concepto="Servicio",
        total_inicial=total,
        origen=origen,
        creado_por=usuario_id,
        created_at=datetime(2026, 1, fecha, tzinfo=timezone.utc),
    )
    db_session.add(cargo)
    db_session.flush()
    return cargo


def test_lista_agrupa_saldos_y_separa_migracion(
    client: TestClient, db_session, referencias_cobros
) -> None:
    persona_a = _persona(db_session, "Ana", "A")
    persona_b = _persona(db_session, "Beto", "B")
    persona_c = _persona(db_session, "Carla", "C")
    cargo_a = _cargo(db_session, persona_a.id, referencias_cobros.usuario_id, 30000)
    cargo_b = _cargo(db_session, persona_b.id, referencias_cobros.usuario_id, 25000)
    _cargo(
        db_session,
        persona_c.id,
        referencias_cobros.usuario_id,
        12000,
        origen=models.OrigenCargo.MIGRACION,
    )
    db_session.commit()
    headers = _auth_token(client, "duenio-cobros")
    pago = client.post(
        f"/api/cargos/{cargo_a.id}/pagos",
        json={"monto_centavos": 25000, "medio": "EFECTIVO"},
        headers=headers,
    )
    assert pago.status_code == 200
    pago_completo = client.post(
        f"/api/cargos/{cargo_b.id}/pagos",
        json={"monto_centavos": 25000, "medio": "EFECTIVO"},
        headers=headers,
    )
    assert pago_completo.status_code == 200
    respuesta = client.get("/api/deudores?orden=monto", headers=headers)
    assert respuesta.status_code == 200
    filas = respuesta.json()
    assert [fila["persona"]["id"] for fila in filas] == [persona_c.id, persona_a.id]
    assert filas[0]["saldo_total_centavos"] == 12000
    assert filas[0]["saldo_migracion_centavos"] == 12000
    assert filas[1]["saldo_total_centavos"] == 5000


def test_resumen_sin_deuda_y_persona_inexistente(
    client: TestClient, referencias_cobros
) -> None:
    headers = _auth_token(client, "duenio-cobros")
    respuesta = client.get(
        f"/api/personas/{referencias_cobros.persona_id}/deuda", headers=headers
    )
    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "debe": False,
        "saldo_total_centavos": 0,
        "cargos_pendientes": 0,
        "deuda_mas_antigua": None,
        "incluye_migracion": False,
    }
    inexistente = client.get("/api/personas/999999/deuda", headers=headers)
    assert inexistente.status_code == 404


def test_saldo_listado_coincide_con_saldo_cargo(
    client: TestClient, db_session, referencias_cobros
) -> None:
    cargo = _cargo(
        db_session, referencias_cobros.persona_id, referencias_cobros.usuario_id, 30000
    )
    db_session.commit()
    headers = _auth_token(client, "duenio-cobros")
    ajuste = client.post(
        f"/api/cargos/{cargo.id}/ajustes",
        json={"nuevo_total_centavos": 28000, "motivo": "Ajuste"},
        headers=headers,
    )
    assert ajuste.status_code == 200
    pago1 = client.post(
        f"/api/cargos/{cargo.id}/pagos",
        json={"monto_centavos": 5000, "medio": "EFECTIVO"},
        headers=headers,
    )
    assert pago1.status_code == 200
    pago2 = client.post(
        f"/api/cargos/{cargo.id}/pagos",
        json={"monto_centavos": 3000, "medio": "EFECTIVO"},
        headers=headers,
    )
    assert pago2.status_code == 200
    reverso = client.post(
        f"/api/pagos/{pago2.json()['id']}/revertir",
        json={"motivo": "Corrección"},
        headers=headers,
    )
    assert reverso.status_code == 200
    respuesta = client.get("/api/deudores", headers=headers)
    assert respuesta.status_code == 200
    fila = respuesta.json()[0]
    assert fila["saldo_total_centavos"] == service.saldo_cargo(db_session, cargo.id)
    assert fila["saldo_total_centavos"] == 23000


def test_limit_mayor_al_maximo_devuelve_422(
    client: TestClient, referencias_cobros
) -> None:
    headers = _auth_token(client, "duenio-cobros")
    respuesta = client.get("/api/deudores?limit=101", headers=headers)
    assert respuesta.status_code == 422


def test_solo_migracion_filtra_por_saldo_migrado(
    client: TestClient, db_session, referencias_cobros
) -> None:
    normal = _persona(db_session, "Nora", "Normal")
    migrada = _persona(db_session, "Marta", "Migrada")
    _cargo(db_session, normal.id, referencias_cobros.usuario_id, 1000)
    _cargo(
        db_session,
        migrada.id,
        referencias_cobros.usuario_id,
        2000,
        origen=models.OrigenCargo.MIGRACION,
    )
    db_session.commit()
    headers = _auth_token(client, "duenio-cobros")
    respuesta = client.get("/api/deudores?solo_migracion=true", headers=headers)
    assert respuesta.status_code == 200
    assert [fila["persona"]["id"] for fila in respuesta.json()] == [migrada.id]


def test_orden_antiguedad_y_dos_cargos_se_agrupan(
    client: TestClient, db_session, referencias_cobros
) -> None:
    primera = _persona(db_session, "Primera", "Persona")
    segunda = _persona(db_session, "Segunda", "Persona")
    _cargo(
        db_session,
        primera.id,
        referencias_cobros.usuario_id,
        5000,
        fecha=2,
    )
    _cargo(
        db_session,
        primera.id,
        referencias_cobros.usuario_id,
        7000,
        fecha=3,
    )
    _cargo(
        db_session,
        segunda.id,
        referencias_cobros.usuario_id,
        9000,
        fecha=1,
    )
    db_session.commit()
    headers = _auth_token(client, "duenio-cobros")
    respuesta = client.get(
        "/api/deudores?orden=antiguedad&limit=1&offset=0", headers=headers
    )
    siguiente = client.get(
        "/api/deudores?orden=antiguedad&limit=1&offset=1", headers=headers
    )
    assert respuesta.status_code == 200
    assert siguiente.status_code == 200
    assert respuesta.json()[0]["persona"]["id"] == segunda.id
    assert siguiente.json()[0]["persona"]["id"] == primera.id
    assert siguiente.json()[0]["cantidad_cargos_pendientes"] == 2
    assert siguiente.json()[0]["saldo_total_centavos"] == 12000


def test_ajuste_saldado_excluye_y_reverso_reincluye(
    client: TestClient, referencias_cobros
) -> None:
    headers = _auth_token(client, "duenio-cobros")
    cargo = client.post(
        "/api/cargos",
        json={
            "persona_id": referencias_cobros.persona_id,
            "concepto": "Ajustable",
            "total_centavos": 30000,
        },
        headers=headers,
    ).json()["id"]
    pago = client.post(
        f"/api/cargos/{cargo}/pagos",
        json={"monto_centavos": 25000, "medio": "EFECTIVO"},
        headers=headers,
    ).json()
    ajuste = client.post(
        f"/api/cargos/{cargo}/ajustes",
        json={"nuevo_total_centavos": 25000, "motivo": "Bonificación"},
        headers=headers,
    )
    assert ajuste.status_code == 200
    assert not any(
        fila["persona"]["id"] == referencias_cobros.persona_id
        for fila in client.get("/api/deudores", headers=headers).json()
    )
    reverso = client.post(
        f"/api/pagos/{pago['id']}/revertir",
        json={"motivo": "Corrección"},
        headers=headers,
    )
    assert reverso.status_code == 200
    assert any(
        fila["persona"]["id"] == referencias_cobros.persona_id
        for fila in client.get("/api/deudores", headers=headers).json()
    )


def test_paginacion_estable_sin_huecos_para_monto_y_antiguedad(
    client: TestClient, db_session, referencias_cobros
) -> None:
    personas = [
        _persona(
            db_session,
            f"Cliente{indice}",
            f"Apellido{indice}",
            confirmar_duplicado=True,
        )
        for indice in range(50)
    ]
    for persona in personas:
        _cargo(
            db_session,
            persona.id,
            referencias_cobros.usuario_id,
            10000,
            fecha=1,
        )
    db_session.commit()
    headers = _auth_token(client, "duenio-cobros")

    for orden in ("monto", "antiguedad"):
        paginas: list[list[int]] = []
        for offset in range(0, 50, 10):
            respuesta = client.get(
                f"/api/deudores?orden={orden}&limit=10&offset={offset}",
                headers=headers,
            )
            assert respuesta.status_code == 200
            paginas.append(
                [fila["persona"]["id"] for fila in respuesta.json()]
            )
        ids = [persona_id for pagina in paginas for persona_id in pagina]
        repetida = client.get(
            f"/api/deudores?orden={orden}&limit=10&offset=0",
            headers=headers,
        )
        assert repetida.status_code == 200
        assert [
            fila["persona"]["id"] for fila in repetida.json()
        ] == paginas[0]
        assert ids == [persona.id for persona in personas]
        assert len(ids) == len(set(ids)) == 50
        assert paginas[0] == [
            fila["persona"]["id"] for fila in repetida.json()
        ]


def test_listado_masivo_y_permisos(
    client: TestClient, db_session, referencias_cobros
) -> None:
    persona = _persona(db_session, "Masiva", "Prueba")
    db_session.bulk_save_objects(
        [
            models.Cargo(
                persona_id=persona.id,
                concepto="Migración masiva",
                total_inicial=1000,
                origen=models.OrigenCargo.NORMAL,
                creado_por=referencias_cobros.usuario_id,
            )
            for _ in range(5000)
        ]
    )
    db_session.commit()
    headers = _auth_token(client, "duenio-cobros")
    inicio = perf_counter()
    respuesta = client.get("/api/deudores?limit=1&offset=0", headers=headers)
    duracion = perf_counter() - inicio
    assert respuesta.status_code == 200
    # Umbral holgado: mide sanidad de la consulta, no la máquina del CI.
    assert duracion < 3

    identidad_service.crear_usuario(
        db_session,
        UsuarioCrear(
            username="personal-deudores",
            password="clave-de-prueba-segura",
            rol=Rol.PERSONAL,
        ),
    )
    identidad_service.crear_usuario(
        db_session,
        UsuarioCrear(
            username="vet-deudores",
            password="clave-de-prueba-segura",
            rol=Rol.VETERINARIO,
        ),
    )
    db_session.commit()
    # El listado global es información financiera: solo el Dueño.
    assert client.get(
        "/api/deudores", headers=_auth_token(client, "personal-deudores")
    ).status_code == 403
    assert client.get(
        "/api/deudores", headers=_auth_token(client, "vet-deudores")
    ).status_code == 403
    assert client.get("/api/deudores").status_code == 401


def test_matriz_de_roles_en_resumen_deuda(
    client: TestClient, db_session, referencias_cobros
) -> None:
    identidad_service.crear_usuario(
        db_session,
        UsuarioCrear(
            username="personal-resumen-deuda",
            password="clave-de-prueba-segura",
            rol=Rol.PERSONAL,
        ),
    )
    identidad_service.crear_usuario(
        db_session,
        UsuarioCrear(
            username="vet-resumen-deuda",
            password="clave-de-prueba-segura",
            rol=Rol.VETERINARIO,
        ),
    )
    db_session.commit()

    ruta = f"/api/personas/{referencias_cobros.persona_id}/deuda"
    assert client.get(ruta).status_code == 401
    assert client.get(
        ruta, headers=_auth_token(client, "duenio-cobros")
    ).status_code == 200
    assert client.get(
        ruta, headers=_auth_token(client, "personal-resumen-deuda")
    ).status_code == 200
    assert client.get(
        ruta, headers=_auth_token(client, "vet-resumen-deuda")
    ).status_code == 403
