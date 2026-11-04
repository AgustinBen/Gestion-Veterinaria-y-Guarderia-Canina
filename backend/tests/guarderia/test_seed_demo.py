from datetime import date

from app.core.parametros import get_param, set_param
from app.modules.cobros import seed as cobros_seed
from app.modules.guarderia import service
from app.modules.guarderia.franjas import Franja
from app.modules.identidad.permisos import Rol
from app.modules.padron import service as padron_service
from app.modules.padron.schemas import PacienteNuevo, PersonaNueva
from app.modules.padron.seed import sembrar_especies_tamanios_tipo_contacto
from scripts.sembrar_guarderia_demo import sembrar_reserva_demo


def test_semilla_ocupa_cupo_publico_minimo_en_dia_y_noche(
    db_session,
    sembrar_cupo,
    crear_usuario,
) -> None:
    cobros_seed.sembrar_medios_pago(db_session)
    sembrar_especies_tamanios_tipo_contacto(db_session)
    especie = next(
        especie
        for especie in padron_service.listar_especies(db_session)
        if especie.nombre == "Perro"
    )
    datos_por_tutor = []
    tutores = (
        ("Ada", "North"),
        ("Bruno", "Lake"),
        ("Camila", "Stone"),
        ("Diego", "West"),
        ("Elena", "Field"),
        ("Felipe", "Cloud"),
        ("Gabriela", "Hill"),
    )
    for indice, (nombre, apellido) in enumerate(tutores):
        tutor = padron_service.crear_persona(
            db_session,
            PersonaNueva(nombre=nombre, apellido=apellido),
            migrado=True,
        )
        paciente = padron_service.crear_paciente(
            db_session,
            PacienteNuevo(
                nombre=f"Mascota {indice}",
                especie_id=especie.id,
                titular_persona_id=tutor.id,
            ),
        )
        datos_por_tutor.append((tutor.id, paciente.id))
    usuario = crear_usuario(Rol.DUENIO)
    fecha = date.today()
    minimo = get_param(db_session, "guarderia.cupo_minimo")
    plazas_emergencia = get_param(db_session, "guarderia.plazas_emergencia")
    objetivo = minimo - plazas_emergencia
    set_param(db_session, "guarderia.cupo_maximo", minimo, "int")

    reservas = [
        sembrar_reserva_demo(
            db_session,
            fecha=fecha,
            desde_franja=Franja.DIA,
            hasta_franja=Franja.NOCHE,
            mascota_clave=f"paciente-{paciente_id}",
            tutor_persona_id=tutor_id,
            paciente_id=paciente_id,
            usuario=usuario,
        )
        for tutor_id, paciente_id in datos_por_tutor
    ]
    repetida = sembrar_reserva_demo(
        db_session,
        fecha=fecha,
        desde_franja=Franja.DIA,
        hasta_franja=Franja.NOCHE,
        mascota_clave=f"paciente-{datos_por_tutor[0][1]}",
        tutor_persona_id=datos_por_tutor[0][0],
        paciente_id=datos_por_tutor[0][1],
        usuario=usuario,
    )

    assert len({reserva[0] for reserva in reservas}) == objetivo
    assert repetida[0] == reservas[0][0]
    assert all(reserva[1] > 0 and 0 < reserva[2] <= reserva[1] for reserva in reservas)
    for franja in (Franja.DIA, Franja.NOCHE):
        disponibilidad = service.calcular_disponibilidad(db_session, fecha, franja)
        assert disponibilidad.ocupado == objetivo
        assert disponibilidad.disponible == 0
    for reserva_id, _, sena in reservas:
        assert service.obtener_reserva(db_session, reserva_id).sena_centavos == sena
