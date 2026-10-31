from datetime import date

from sqlalchemy import func, select

from app.core.parametros import set_param
from app.modules.guarderia import cupo, service
from app.modules.guarderia.cupo import plazas_por_animal
from app.modules.guarderia.franjas import Franja
from app.modules.guarderia.models import (
    EstadoReserva,
    HabilitacionEmergencia,
    Ocupacion,
)
from app.modules.guarderia.schemas import FranjaSinLugar


def test_plazas_por_animal_no_depende_de_tamanio_ni_especie() -> None:
    pacientes = [
        {"especie": "PERRO", "tamanio": "GRANDE"},
        {"especie": "PERRO", "tamanio": "MEDIANO"},
        {"especie": "PERRO", "tamanio": "CHICO"},
        {"especie": "GATO", "tamanio": None},
    ]

    assert [plazas_por_animal(paciente) for paciente in pacientes] == [1, 1, 1, 1]


FECHA = date(2030, 12, 15)


def _perros(cantidad: int) -> list[tuple[str, str | None]]:
    return [("Perro", None) for _ in range(cantidad)]


def _habilitar(
    db_session,
    fecha: date,
    franja: Franja,
    usuario_id: int,
) -> None:
    db_session.add(
        HabilitacionEmergencia(
            fecha=fecha,
            franja=franja,
            usuario_id=usuario_id,
            motivo="Necesidad de prueba",
        )
    )
    db_session.flush()


def test_lleno_justo_acepta_una_reserva(
    db_session,
    sembrar_cupo,
    crear_pacientes,
    crear_ocupaciones,
    crear_usuario,
) -> None:
    usuario = crear_usuario()
    ocupados = crear_pacientes(_perros(8))
    nuevo = crear_pacientes(_perros(1))
    crear_ocupaciones(ocupados, FECHA, Franja.DIA, usuario.id)

    disponibilidad = service.calcular_disponibilidad(db_session, FECHA, Franja.DIA)
    resultado = service.verificar_cupo(
        db_session, nuevo, (FECHA, Franja.DIA), (FECHA, Franja.DIA)
    )

    assert disponibilidad.publico == 9
    assert disponibilidad.ocupado == 8
    assert disponibilidad.disponible == 1
    assert resultado.aprobado is True
    assert resultado.codigo == "DISPONIBLE"


def test_uno_mas_rechaza_y_detalla_fecha_y_franja(
    db_session,
    sembrar_cupo,
    crear_pacientes,
    crear_ocupaciones,
    crear_usuario,
) -> None:
    usuario = crear_usuario()
    ocupados = crear_pacientes(_perros(9))
    nuevo = crear_pacientes(_perros(1))
    crear_ocupaciones(ocupados, FECHA, Franja.DIA, usuario.id)

    resultado = service.verificar_cupo(
        db_session, nuevo, (FECHA, Franja.DIA), (FECHA, Franja.DIA)
    )

    assert resultado.aprobado is False
    assert resultado.codigo == "SIN_CUPO"
    assert resultado.franjas_sin_lugar == [
        FranjaSinLugar(
            fecha=FECHA,
            franja=Franja.DIA,
            necesita=1,
            disponible=0,
        )
    ]


def test_perros_y_gatos_comparten_cupo_y_tamanio_no_interviene(
    db_session,
    sembrar_cupo,
    crear_pacientes,
    crear_ocupaciones,
    crear_usuario,
) -> None:
    usuario = crear_usuario()
    perros = crear_pacientes(
        [("Perro", "Grande"), ("Perro", "Mediano"), ("Perro", "Chico")]
        + _perros(2)
    )
    gatos = crear_pacientes([("Gato", None) for _ in range(4)])
    nuevo = crear_pacientes([("Gato", None)])
    crear_ocupaciones(perros + gatos, FECHA, Franja.DIA, usuario.id)

    disponibilidad = service.calcular_disponibilidad(db_session, FECHA, Franja.DIA)
    resultado = service.verificar_cupo(
        db_session, nuevo, (FECHA, Franja.DIA), (FECHA, Franja.DIA)
    )

    assert disponibilidad.ocupado == 9
    assert resultado.codigo == "SIN_CUPO"


def test_dia_lleno_no_impide_reservar_noche(
    db_session,
    sembrar_cupo,
    crear_pacientes,
    crear_ocupaciones,
    crear_usuario,
) -> None:
    usuario = crear_usuario()
    ocupados = crear_pacientes(_perros(9))
    nuevo = crear_pacientes(_perros(1))
    crear_ocupaciones(ocupados, FECHA, Franja.DIA, usuario.id)

    resultado = service.verificar_cupo(
        db_session, nuevo, (FECHA, Franja.NOCHE), (FECHA, Franja.NOCHE)
    )

    assert resultado.aprobado is True
    assert resultado.franjas_sin_lugar == []


def test_estadia_de_24_horas_se_rechaza_si_una_franja_esta_llena(
    db_session,
    sembrar_cupo,
    crear_pacientes,
    crear_ocupaciones,
    crear_usuario,
) -> None:
    usuario = crear_usuario()
    ocupados = crear_pacientes(_perros(9))
    nuevo = crear_pacientes(_perros(1))
    crear_ocupaciones(ocupados, FECHA, Franja.NOCHE, usuario.id)

    resultado = service.verificar_cupo(
        db_session,
        nuevo,
        (FECHA, Franja.DIA),
        (FECHA, Franja.NOCHE),
    )

    assert resultado.codigo == "SIN_CUPO"
    assert [(fila.fecha, fila.franja) for fila in resultado.franjas_sin_lugar] == [
        (FECHA, Franja.NOCHE)
    ]


def test_habilitacion_emergencia_es_por_fecha_y_limitada_por_configuracion(
    db_session,
    sembrar_cupo,
    crear_pacientes,
    crear_ocupaciones,
    crear_usuario,
) -> None:
    usuario = crear_usuario()
    ocupados = crear_pacientes(_perros(9))
    nuevo = crear_pacientes(_perros(1))
    crear_ocupaciones(ocupados, FECHA, Franja.DIA, usuario.id)

    sin_habilitacion = service.verificar_cupo(
        db_session, nuevo, (FECHA, Franja.DIA), (FECHA, Franja.DIA)
    )
    _habilitar(db_session, date(2030, 12, 16), Franja.DIA, usuario.id)
    habilitada_otro_dia = service.verificar_cupo(
        db_session, nuevo, (FECHA, Franja.DIA), (FECHA, Franja.DIA)
    )
    _habilitar(db_session, FECHA, Franja.DIA, usuario.id)
    _habilitar(db_session, FECHA, Franja.DIA, usuario.id)
    con_habilitacion = service.verificar_cupo(
        db_session, nuevo, (FECHA, Franja.DIA), (FECHA, Franja.DIA)
    )
    disponibilidad = service.calcular_disponibilidad(db_session, FECHA, Franja.DIA)

    assert sin_habilitacion.codigo == "SIN_CUPO"
    assert habilitada_otro_dia.codigo == "SIN_CUPO"
    assert con_habilitacion.aprobado is True
    assert disponibilidad.habilitadas == 1
    assert disponibilidad.publico == 10


def test_bajar_cupo_no_cancela_ocupaciones_existentes(
    db_session,
    sembrar_cupo,
    crear_pacientes,
    crear_ocupaciones,
    crear_usuario,
) -> None:
    usuario = crear_usuario()
    ocupados = crear_pacientes(_perros(7))
    nuevo = crear_pacientes(_perros(1))
    crear_ocupaciones(ocupados, FECHA, Franja.DIA, usuario.id)
    set_param(db_session, "guarderia.cupo_maximo", 8, "int")

    resultado = service.verificar_cupo(
        db_session, nuevo, (FECHA, Franja.DIA), (FECHA, Franja.DIA)
    )
    cantidad_ocupaciones = db_session.execute(
        select(func.count(Ocupacion.id))
    ).scalar_one()

    assert resultado.codigo == "SIN_CUPO"
    assert service.calcular_disponibilidad(db_session, FECHA, Franja.DIA).publico == 7
    assert cantidad_ocupaciones == 7


def test_disponible_puede_ser_negativo_si_cupo_baja_de_ocupacion_existente(
    db_session,
    sembrar_cupo,
    crear_pacientes,
    crear_ocupaciones,
    crear_usuario,
) -> None:
    usuario = crear_usuario()
    ocupados = crear_pacientes(_perros(9))
    nuevo = crear_pacientes(_perros(1))
    crear_ocupaciones(ocupados, FECHA, Franja.DIA, usuario.id)
    set_param(db_session, "guarderia.cupo_maximo", 8, "int")

    disponibilidad = service.calcular_disponibilidad(db_session, FECHA, Franja.DIA)
    resultado = service.verificar_cupo(
        db_session, nuevo, (FECHA, Franja.DIA), (FECHA, Franja.DIA)
    )

    assert disponibilidad.publico == 7
    assert disponibilidad.ocupado == 9
    assert disponibilidad.disponible == -2
    assert resultado.codigo == "SIN_CUPO"
    assert resultado.franjas_sin_lugar[0].disponible == -2


def test_pedido_de_varios_animales_necesita_plaza_para_cada_uno(
    db_session,
    sembrar_cupo,
    crear_pacientes,
    crear_ocupaciones,
    crear_usuario,
) -> None:
    usuario = crear_usuario()
    ocupados = crear_pacientes(_perros(8))
    pedido = crear_pacientes(_perros(2))
    crear_ocupaciones(ocupados, FECHA, Franja.DIA, usuario.id)

    resultado = service.verificar_cupo(
        db_session, pedido, (FECHA, Franja.DIA), (FECHA, Franja.DIA)
    )

    assert resultado.codigo == "SIN_CUPO"
    assert resultado.franjas_sin_lugar[0].necesita == 2
    assert resultado.franjas_sin_lugar[0].disponible == 1


def test_cambio_de_parametro_se_refleja_en_el_calculo_siguiente(
    db_session,
    sembrar_cupo,
) -> None:
    inicial = service.calcular_disponibilidad(db_session, FECHA, Franja.DIA)
    set_param(db_session, "guarderia.cupo_maximo", 8, "int")
    actualizado = service.calcular_disponibilidad(db_session, FECHA, Franja.DIA)

    assert inicial.publico == 9
    assert actualizado.publico == 7


def test_plazas_por_animal_es_la_unica_regla_usada_en_disponibilidad_y_verificacion(
    db_session,
    sembrar_cupo,
    crear_pacientes,
    crear_ocupaciones,
    crear_usuario,
    monkeypatch,
) -> None:
    usuario = crear_usuario()
    ocupados = crear_pacientes(_perros(4))
    nuevo = crear_pacientes(_perros(1))
    crear_ocupaciones(ocupados, FECHA, Franja.DIA, usuario.id)

    normal = service.verificar_cupo(
        db_session, nuevo, (FECHA, Franja.DIA), (FECHA, Franja.DIA)
    )
    monkeypatch.setattr(cupo, "plazas_por_animal", lambda _paciente: 2)

    disponibilidad = service.calcular_disponibilidad(db_session, FECHA, Franja.DIA)
    resultado = service.verificar_cupo(
        db_session, nuevo, (FECHA, Franja.DIA), (FECHA, Franja.DIA)
    )
    calendario = service.calendario(db_session, FECHA, FECHA)

    assert normal.aprobado is True
    assert disponibilidad.ocupado == 8
    assert disponibilidad.disponible == 1
    assert resultado.codigo == "SIN_CUPO"
    assert resultado.franjas_sin_lugar[0].necesita == 2
    assert calendario[0].ocupado == 8
    assert calendario[0].disponible == 1


def test_paciente_ocupado_en_una_franja_se_informa_como_ya_reservado(
    db_session,
    sembrar_cupo,
    crear_pacientes,
    crear_ocupaciones,
    crear_usuario,
) -> None:
    usuario = crear_usuario()
    paciente = crear_pacientes(_perros(1))
    crear_ocupaciones(paciente, FECHA, Franja.NOCHE, usuario.id)

    resultado = service.verificar_cupo(
        db_session,
        paciente,
        (FECHA, Franja.DIA),
        (FECHA, Franja.NOCHE),
    )

    assert resultado.aprobado is False
    assert resultado.codigo == "YA_RESERVADO"
    assert resultado.ocupaciones_existentes[0].franja == Franja.NOCHE


def test_verificar_cupo_consulta_pacientes_ocupados_y_pedido_en_un_solo_lote(
    db_session,
    sembrar_cupo,
    crear_pacientes,
    crear_ocupaciones,
    crear_usuario,
    monkeypatch,
) -> None:
    usuario = crear_usuario()
    ocupado = crear_pacientes(_perros(1))
    pedido = crear_pacientes(_perros(1))
    crear_ocupaciones(ocupado, FECHA, Franja.DIA, usuario.id)
    consultar_lote = service.padron_service.obtener_pacientes
    lotes: list[set[int]] = []

    def registrar_lote(db, paciente_ids: list[int]):
        lotes.append(set(paciente_ids))
        return consultar_lote(db, paciente_ids)

    monkeypatch.setattr(
        service.padron_service, "obtener_pacientes", registrar_lote
    )

    resultado = service.verificar_cupo(
        db_session, pedido, (FECHA, Franja.DIA), (FECHA, Franja.DIA)
    )

    assert resultado.aprobado is True
    assert lotes == [set(ocupado + pedido)]


def test_ocupacion_pendiente_de_sena_reserva_la_plaza(
    db_session,
    sembrar_cupo,
    crear_pacientes,
    crear_ocupaciones,
    crear_usuario,
) -> None:
    usuario = crear_usuario()
    paciente = crear_pacientes(_perros(1))
    crear_ocupaciones(
        paciente,
        FECHA,
        Franja.DIA,
        usuario.id,
        estado=EstadoReserva.PENDIENTE_SENA,
    )

    disponibilidad = service.calcular_disponibilidad(db_session, FECHA, Franja.DIA)

    assert disponibilidad.ocupado == 1
