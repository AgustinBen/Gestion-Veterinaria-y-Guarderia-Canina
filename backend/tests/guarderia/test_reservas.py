from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy import func, select

from app.core.parametros import get_param, set_param
from app.modules.cobros import service as cobros_service
from app.modules.guarderia import service as guarderia_service
from app.modules.guarderia.franjas import Franja
from app.modules.guarderia.models import Ocupacion, Reserva
from app.modules.guarderia.schemas import ReservaCrear
from app.modules.guarderia.seed import RESERVA_MAX_MESES_INICIAL
from app.modules.guarderia.tramos import franjas_del_tramo
from app.modules.identidad.permisos import Rol
from app.modules.padron import service as padron_service
from app.modules.padron.schemas import PacienteActualizar


def _payload(
    tutor_persona_id: int,
    paciente_ids: list[int],
    *,
    desde_fecha: date | None = None,
    desde_franja: Franja = Franja.DIA,
    hasta_fecha: date | None = None,
    hasta_franja: Franja = Franja.DIA,
) -> dict[str, object]:
    inicio = desde_fecha or date.today() + timedelta(days=2)
    fin = hasta_fecha or inicio
    return {
        "tutor_persona_id": tutor_persona_id,
        "paciente_ids": paciente_ids,
        "desde_fecha": inicio.isoformat(),
        "desde_franja": desde_franja.value,
        "hasta_fecha": fin.isoformat(),
        "hasta_franja": hasta_franja.value,
        "cuidados_extras": [
            {"paciente_id": paciente_id, "cuidados_extras": False}
            for paciente_id in paciente_ids
        ],
        "total_centavos": 300000,
    }


def _crear(
    client,
    headers: dict[str, str],
    payload: dict[str, object],
    key: str = "reserva-key",
):
    return client.post(
        "/api/guarderia/reservas",
        json=payload,
        headers={**headers, "Idempotency-Key": key},
    )


def test_crear_reserva_pendiente_ocupa_cupo_y_crea_cargo(
    client,
    db_session,
    sembrar_cupo,
    crear_datos_reserva,
    crear_usuario,
    token_guarderia,
) -> None:
    datos = crear_datos_reserva()
    usuario = crear_usuario(Rol.DUENIO)

    respuesta = _crear(
        client,
        token_guarderia(usuario),
        _payload(datos.tutor_persona_id, datos.paciente_ids),
    )

    assert respuesta.status_code == 201
    reserva = respuesta.json()
    assert reserva["estado"] == "PENDIENTE_SENA"
    assert reserva["cargo_id"] is not None
    assert reserva["total_centavos"] == 300000
    assert len(reserva["pacientes"]) == 1
    assert db_session.scalar(
        select(func.count(Ocupacion.id)).where(
            Ocupacion.reserva_id == reserva["id"]
        )
    ) == 1
    detalle_cargo = cobros_service.obtener_cargo_detalle(
        db_session, reserva["cargo_id"]
    )
    assert detalle_cargo["saldo"] == 300000


def test_idempotencia_devuelve_la_misma_reserva_o_conflicto_por_cuerpo(
    client,
    db_session,
    sembrar_cupo,
    crear_datos_reserva,
    crear_usuario,
    token_guarderia,
) -> None:
    datos = crear_datos_reserva()
    usuario = crear_usuario(Rol.DUENIO)
    headers = token_guarderia(usuario)
    payload = _payload(datos.tutor_persona_id, datos.paciente_ids)

    primera = _crear(client, headers, payload, "reintento-key")
    segunda = _crear(client, headers, payload, "reintento-key")
    distinta = dict(payload, total_centavos=301000)

    conflicto = _crear(client, headers, distinta, "reintento-key")

    assert primera.status_code == 201
    assert segunda.status_code == 200
    assert segunda.json()["id"] == primera.json()["id"]
    assert conflicto.status_code == 409
    assert conflicto.json()["detail"]["codigo"] == "IDEMPOTENCIA_CONFLICTO"
    assert db_session.scalar(select(func.count(Reserva.id))) == 1


def test_persiste_detalle_de_cuidados_y_lo_incluye_en_idempotencia(
    client,
    sembrar_cupo,
    crear_datos_reserva,
    crear_usuario,
    token_guarderia,
) -> None:
    datos = crear_datos_reserva()
    usuario = crear_usuario(Rol.DUENIO)
    headers = token_guarderia(usuario)
    paciente_id = datos.paciente_ids[0]
    payload = _payload(datos.tutor_persona_id, [paciente_id])
    payload["cuidados_extras"] = [
        {
            "paciente_id": paciente_id,
            "cuidados_extras": True,
            "tipo_cuidado": "Administrar medicación",
        }
    ]

    creada = _crear(client, headers, payload, "reserva-cuidado")
    reintentada = _crear(client, headers, payload, "reserva-cuidado")
    otra_solicitud = dict(payload)
    otra_solicitud["cuidados_extras"] = [
        {
            "paciente_id": paciente_id,
            "cuidados_extras": True,
            "tipo_cuidado": "Cuidado diferente",
        }
    ]
    conflicto = _crear(client, headers, otra_solicitud, "reserva-cuidado")

    assert creada.status_code == 201
    assert creada.json()["pacientes"][0]["tipo_cuidado"] == "Administrar medicación"
    assert reintentada.status_code == 200
    assert conflicto.status_code == 409


@pytest.mark.parametrize(
    ("cambios", "codigo"),
    [
        ({"desde_fecha": (date.today() - timedelta(days=1)).isoformat(),
          "hasta_fecha": (date.today() - timedelta(days=1)).isoformat()}, 422),
        ({"desde_fecha": (date.today() + timedelta(days=3)).isoformat(),
          "hasta_fecha": (date.today() + timedelta(days=2)).isoformat()}, 422),
    ],
)
def test_rechaza_fechas_pasadas_o_tramos_invertidos(
    client,
    sembrar_cupo,
    crear_datos_reserva,
    crear_usuario,
    token_guarderia,
    cambios: dict[str, object],
    codigo: int,
) -> None:
    datos = crear_datos_reserva()
    usuario = crear_usuario(Rol.DUENIO)
    payload = _payload(datos.tutor_persona_id, datos.paciente_ids)
    payload.update(cambios)

    respuesta = _crear(client, token_guarderia(usuario), payload)

    assert respuesta.status_code == codigo


def test_rechaza_tutor_sin_titularidad_vigente(
    client,
    sembrar_cupo,
    crear_datos_reserva,
    crear_usuario,
    token_guarderia,
) -> None:
    datos = crear_datos_reserva()
    usuario = crear_usuario(Rol.DUENIO)
    payload = _payload(datos.otro_tutor_persona_id, datos.paciente_ids)

    respuesta = _crear(client, token_guarderia(usuario), payload)

    assert respuesta.status_code == 422


def test_rechaza_paciente_repetido(
    client,
    sembrar_cupo,
    crear_datos_reserva,
    crear_usuario,
    token_guarderia,
) -> None:
    datos = crear_datos_reserva()
    usuario = crear_usuario(Rol.DUENIO)
    paciente_id = datos.paciente_ids[0]
    payload = _payload(datos.tutor_persona_id, [paciente_id, paciente_id])

    respuesta = _crear(client, token_guarderia(usuario), payload)

    assert respuesta.status_code == 422


def test_rechaza_paciente_inexistente_y_total_no_positivo(
    client,
    sembrar_cupo,
    crear_datos_reserva,
    crear_usuario,
    token_guarderia,
) -> None:
    datos = crear_datos_reserva()
    usuario = crear_usuario(Rol.DUENIO)
    headers = token_guarderia(usuario)
    paciente_inexistente = _payload(datos.tutor_persona_id, [999999])
    total_cero = _payload(datos.tutor_persona_id, datos.paciente_ids)
    total_cero["total_centavos"] = 0

    respuesta_paciente = _crear(client, headers, paciente_inexistente)
    respuesta_total = _crear(client, headers, total_cero, "total-cero")

    assert respuesta_paciente.status_code == 422
    assert respuesta_total.status_code == 422


def test_rechaza_paciente_inactivo(
    client,
    db_session,
    sembrar_cupo,
    crear_datos_reserva,
    crear_usuario,
    token_guarderia,
) -> None:
    datos = crear_datos_reserva()
    usuario = crear_usuario(Rol.DUENIO)
    padron_service.actualizar_paciente(
        db_session,
        datos.paciente_ids[0],
        PacienteActualizar(activo=False),
    )

    respuesta = _crear(
        client,
        token_guarderia(usuario),
        _payload(datos.tutor_persona_id, datos.paciente_ids),
    )

    assert respuesta.status_code == 422


def test_rechaza_reserva_mas_alla_de_la_anticipacion_configurada(
    client,
    db_session,
    sembrar_cupo,
    crear_datos_reserva,
    crear_usuario,
    token_guarderia,
) -> None:
    datos = crear_datos_reserva()
    usuario = crear_usuario(Rol.DUENIO)
    fecha_limite = guarderia_service._sumar_meses(
        date.today(),
        get_param(db_session, "guarderia.reserva_max_meses"),
    )
    fecha_excedida = fecha_limite + timedelta(days=1)

    respuesta = _crear(
        client,
        token_guarderia(usuario),
        _payload(
            datos.tutor_persona_id,
            datos.paciente_ids,
            desde_fecha=fecha_excedida,
        ),
    )

    assert respuesta.status_code == 422
    assert "anticipación máxima" in respuesta.json()["detail"]


def test_reserva_en_el_limite_configurado_es_valida(
    client,
    db_session,
    sembrar_cupo,
    crear_datos_reserva,
    crear_usuario,
    token_guarderia,
) -> None:
    datos = crear_datos_reserva()
    usuario = crear_usuario(Rol.DUENIO)
    fecha_limite = guarderia_service._sumar_meses(
        date.today(),
        get_param(db_session, "guarderia.reserva_max_meses"),
    )

    respuesta = _crear(
        client,
        token_guarderia(usuario),
        _payload(
            datos.tutor_persona_id,
            datos.paciente_ids,
            desde_fecha=fecha_limite,
        ),
    )

    assert respuesta.status_code == 201


def test_limite_de_anticipacion_usa_el_parametro_configurado(
    db_session,
    sembrar_cupo,
    crear_datos_reserva,
    crear_usuario,
) -> None:
    datos = crear_datos_reserva()
    usuario = crear_usuario(Rol.DUENIO)
    meses_personalizados = RESERVA_MAX_MESES_INICIAL - 1
    set_param(
        db_session,
        "guarderia.reserva_max_meses",
        meses_personalizados,
        "int",
        modulo="guarderia",
    )
    fecha_excedida = guarderia_service._sumar_meses(
        date.today(),
        meses_personalizados,
    ) + timedelta(days=1)
    solicitud = ReservaCrear.model_validate(
        _payload(
            datos.tutor_persona_id,
            datos.paciente_ids,
            desde_fecha=fecha_excedida,
        )
    )

    with pytest.raises(guarderia_service.ReservaInvalida, match="anticipación máxima"):
        guarderia_service.crear_reserva(
            db_session,
            solicitud,
            clave_idempotencia="limite-configurado",
            usuario_id=usuario.id,
        )


def test_sin_cupo_devuelve_franjas_que_no_tienen_lugar(
    client,
    db_session,
    sembrar_cupo,
    crear_datos_reserva,
    crear_pacientes,
    crear_ocupaciones,
    crear_usuario,
    token_guarderia,
) -> None:
    datos = crear_datos_reserva()
    usuario = crear_usuario(Rol.DUENIO)
    cupo_publico = (
        get_param(db_session, "guarderia.cupo_maximo")
        - get_param(db_session, "guarderia.plazas_emergencia")
    )
    fecha = date.today() + timedelta(days=2)
    for paciente_id in crear_pacientes([("Perro", None)] * cupo_publico):
        crear_ocupaciones(
            [paciente_id],
            fecha,
            Franja.DIA,
            usuario.id,
        )
    db_session.commit()

    respuesta = _crear(
        client,
        token_guarderia(usuario),
        _payload(
            datos.tutor_persona_id,
            datos.paciente_ids,
            desde_fecha=fecha,
        ),
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["codigo"] == "SIN_CUPO"
    assert respuesta.json()["detail"]["franjas_sin_lugar"] == [
        {
            "fecha": fecha.isoformat(),
            "franja": "DIA",
            "necesita": 1,
            "disponible": 0,
        }
    ]


def test_total_de_reserva_refleja_ajuste_de_precio_de_cobros(
    client,
    db_session,
    sembrar_cupo,
    crear_datos_reserva,
    crear_usuario,
    token_guarderia,
) -> None:
    datos = crear_datos_reserva()
    usuario = crear_usuario(Rol.DUENIO)
    headers = token_guarderia(usuario)
    creada = _crear(
        client,
        headers,
        _payload(datos.tutor_persona_id, datos.paciente_ids),
        "reserva-precio-ajustado",
    )
    cargo_id = creada.json()["cargo_id"]
    cobros_service.ajustar_precio(
        db_session,
        cargo_id=cargo_id,
        nuevo_total_centavos=200000,
        motivo="Ajuste de prueba",
        usuario_id=usuario.id,
        rol=Rol.DUENIO,
    )

    detalle = client.get(
        f"/api/guarderia/reservas/{creada.json()['id']}",
        headers=headers,
    )
    listado = client.get("/api/guarderia/reservas", headers=headers)

    assert detalle.status_code == 200
    assert detalle.json()["total_centavos"] == 200000
    assert listado.status_code == 200
    assert listado.json()[0]["total_centavos"] == 200000


def test_fallo_al_crear_cargo_revierte_reserva_y_ocupacion(
    db_session,
    sembrar_cupo,
    crear_datos_reserva,
    crear_usuario,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    datos = crear_datos_reserva()
    usuario = crear_usuario(Rol.DUENIO)
    solicitud = ReservaCrear.model_validate(
        _payload(datos.tutor_persona_id, datos.paciente_ids)
    )

    def falla_crear_cargo(*args, **kwargs):
        raise RuntimeError("fallo forzado de Cobros")

    monkeypatch.setattr(cobros_service, "crear_cargo", falla_crear_cargo)
    with pytest.raises(RuntimeError, match="fallo forzado"):
        guarderia_service.crear_reserva(
            db_session,
            solicitud,
            clave_idempotencia="fallo-cargo",
            usuario_id=usuario.id,
        )

    assert db_session.scalar(
        select(func.count(Reserva.id)).where(
            Reserva.clave_idempotencia == "fallo-cargo"
        )
    ) == 0
    assert db_session.scalar(select(func.count(Ocupacion.id))) == 0


def test_rechaza_otra_reserva_del_mismo_animal_en_el_tramo(
    client,
    sembrar_cupo,
    crear_datos_reserva,
    crear_usuario,
    token_guarderia,
) -> None:
    datos = crear_datos_reserva()
    usuario = crear_usuario(Rol.DUENIO)
    headers = token_guarderia(usuario)
    payload = _payload(datos.tutor_persona_id, datos.paciente_ids)

    primera = _crear(client, headers, payload, "ocupacion-uno")
    segunda = _crear(client, headers, payload, "ocupacion-dos")

    assert primera.status_code == 201
    assert segunda.status_code == 409
    assert segunda.json()["detail"]["codigo"] == "YA_RESERVADO"


def test_reserva_dos_animales_en_dia_y_noche_ocupa_cuatro_franjas(
    client,
    db_session,
    sembrar_cupo,
    crear_datos_reserva,
    crear_usuario,
    token_guarderia,
) -> None:
    datos = crear_datos_reserva(cantidad_pacientes=2)
    usuario = crear_usuario(Rol.DUENIO)
    payload = _payload(
        datos.tutor_persona_id,
        datos.paciente_ids,
        desde_franja=Franja.DIA,
        hasta_franja=Franja.NOCHE,
    )

    respuesta = _crear(client, token_guarderia(usuario), payload)

    assert respuesta.status_code == 201
    tramos = franjas_del_tramo(
        date.fromisoformat(payload["desde_fecha"]),
        Franja(payload["desde_franja"]),
        date.fromisoformat(payload["hasta_fecha"]),
        Franja(payload["hasta_franja"]),
    )
    assert db_session.scalar(
        select(func.count(Ocupacion.id)).where(
            Ocupacion.reserva_id == respuesta.json()["id"]
        )
    ) == len(datos.paciente_ids) * len(tramos)


def test_un_deudor_puede_crear_una_reserva(
    client,
    db_session,
    sembrar_cupo,
    crear_datos_reserva,
    crear_usuario,
    token_guarderia,
) -> None:
    datos = crear_datos_reserva()
    usuario = crear_usuario(Rol.DUENIO)
    cobros_service.crear_cargo(
        db_session,
        persona_id=datos.tutor_persona_id,
        concepto="Deuda previa",
        total_centavos=100000,
        usuario_id=usuario.id,
    )

    respuesta = _crear(
        client,
        token_guarderia(usuario),
        _payload(datos.tutor_persona_id, datos.paciente_ids),
        "deudor-key",
    )

    assert respuesta.status_code == 201


def test_obtener_y_listar_reservas(
    client,
    sembrar_cupo,
    crear_datos_reserva,
    crear_usuario,
    token_guarderia,
) -> None:
    datos = crear_datos_reserva()
    usuario = crear_usuario(Rol.DUENIO)
    headers = token_guarderia(usuario)
    payload = _payload(datos.tutor_persona_id, datos.paciente_ids)
    creada = _crear(client, headers, payload, "lectura-key")
    reserva_id = creada.json()["id"]

    detalle = client.get(
        f"/api/guarderia/reservas/{reserva_id}",
        headers=headers,
    )
    listado = client.get(
        "/api/guarderia/reservas",
        params={"persona_id": datos.tutor_persona_id, "estado": "PENDIENTE_SENA"},
        headers=headers,
    )

    assert detalle.status_code == 200
    assert listado.status_code == 200
    assert [reserva["id"] for reserva in listado.json()] == [reserva_id]
