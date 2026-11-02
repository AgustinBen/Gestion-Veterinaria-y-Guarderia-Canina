"""Escenario sembrado del panel financiero (T-46).

Números conocidos (en centavos):
- Guardería: pagos 2.000 + 28.000 en efectivo, reverso de 2.000 → neto 28.000.
- Consulta: pago 12.000 en débito.
- Ingresos: 28.000 + 12.000 = 40.000.
- Egreso operativo: 8.000. Gasto a externo vinculado a guardería: 5.000.
- Rentabilidad neta: 40.000 - 8.000 - 5.000 = 27.000.
- Deuda: 7.000 de un cliente, aparte de la rentabilidad.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.cobros import seed as cobros_seed
from app.modules.cobros import service as cobros_service
from app.modules.cobros.schemas import TipoServicio
from app.modules.identidad import service as identidad_service
from app.modules.identidad.permisos import Rol
from app.modules.identidad.schemas import UsuarioCrear
from app.modules.padron import service as padron_service
from app.modules.padron.schemas import EmpleadoNuevo, PacienteNuevo, PersonaNueva
from app.modules.padron.seed import sembrar_especies_tamanios_tipo_contacto
from app.modules.panel import models as panel_models

PASSWORD = "clave-de-prueba-segura"


@dataclass(frozen=True)
class EscenarioPanel:
    persona_id: int
    persona_deudora_id: int
    paciente_id: int
    empleado_id: int
    usuario_id: int
    cargo_guarderia_id: int
    cargo_consulta_id: int
    fecha: date
    desde: date
    hasta: date


@pytest.fixture
def panel_escenario(db_session: Session) -> EscenarioPanel:
    sembrar_especies_tamanios_tipo_contacto(db_session)
    cobros_seed.sembrar_medios_pago(db_session)

    persona = padron_service.crear_persona(
        db_session, PersonaNueva(nombre="Tutora", apellido="Panel"), migrado=True
    )
    persona_deudora = padron_service.crear_persona(
        db_session, PersonaNueva(nombre="Cliente", apellido="Deudor"), migrado=True
    )
    especie_id = next(
        especie.id
        for especie in padron_service.listar_especies(db_session)
        if especie.nombre == "Perro"
    )
    paciente = padron_service.crear_paciente(
        db_session,
        PacienteNuevo(
            nombre="Firulais", especie_id=especie_id, titular_persona_id=persona.id
        ),
    )
    empleado = padron_service.crear_empleado(
        db_session,
        EmpleadoNuevo(
            persona=PersonaNueva(
                nombre="Veterinario",
                apellido="Externo",
                dni="30111224",
                telefonos=["11 5555-0202"],
            ),
            tipo="EXTERNO",
            es_veterinario=True,
        ),
    )
    usuario = identidad_service.crear_usuario(
        db_session,
        UsuarioCrear(
            username="duenio-panel", password=PASSWORD, rol=Rol.DUENIO
        ),
    )

    hoy = date.today()
    fecha = hoy - timedelta(days=5)
    desde = hoy - timedelta(days=10)
    hasta = hoy + timedelta(days=10)

    cargo_guarderia = cobros_service.crear_cargo(
        db_session,
        persona_id=persona.id,
        paciente_id=paciente.id,
        concepto="Guardería",
        total_centavos=30_000,
        tipo_servicio=TipoServicio.GUARDERIA,
        usuario_id=usuario.id,
    )
    pago_2000 = cobros_service.registrar_pago(
        db_session,
        cargo_id=cargo_guarderia.id,
        monto_centavos=2_000,
        medio="EFECTIVO",
        usuario_id=usuario.id,
        fecha_pago=fecha,
    )
    cobros_service.registrar_pago(
        db_session,
        cargo_id=cargo_guarderia.id,
        monto_centavos=28_000,
        medio="EFECTIVO",
        usuario_id=usuario.id,
        fecha_pago=fecha,
    )
    cobros_service.revertir_pago(
        db_session,
        pago_id=pago_2000.id,
        usuario_id=usuario.id,
        motivo="Error de cobro",
    )
    # El reverso deja 2.000 de saldo: se ajusta el total para que el cliente
    # quede al día y la deuda del escenario sea solo la del otro cliente.
    cobros_service.ajustar_precio(
        db_session,
        cargo_id=cargo_guarderia.id,
        nuevo_total_centavos=28_000,
        motivo="Ajuste tras reverso",
        usuario_id=usuario.id,
        rol=Rol.DUENIO,
    )

    cargo_consulta = cobros_service.crear_cargo(
        db_session,
        persona_id=persona.id,
        concepto="Consulta",
        total_centavos=12_000,
        tipo_servicio=TipoServicio.CONSULTA,
        usuario_id=usuario.id,
    )
    cobros_service.registrar_pago(
        db_session,
        cargo_id=cargo_consulta.id,
        monto_centavos=12_000,
        medio="DEBITO",
        usuario_id=usuario.id,
        fecha_pago=fecha,
    )

    categoria = panel_models.CategoriaEgreso(
        nombre="Operativos", nombre_normalizado="operativos", activa=True
    )
    db_session.add(categoria)
    db_session.flush()
    db_session.add(
        panel_models.Egreso(
            fecha=fecha,
            monto_centavos=8_000,
            categoria_id=categoria.id,
            descripcion="Luz",
            registrado_por=usuario.id,
        )
    )
    db_session.add(
        panel_models.Egreso(
            fecha=fecha,
            monto_centavos=9_900,
            categoria_id=categoria.id,
            descripcion="Anulado",
            registrado_por=usuario.id,
            anulado_en=datetime.now(timezone.utc),
            anulado_por=usuario.id,
            motivo_anulacion="Carga duplicada",
        )
    )
    db_session.commit()

    cobros_service.registrar_gasto_externo(
        db_session,
        empleado_externo_id=empleado.persona_id,
        descripcion="Cirugía",
        monto_centavos=5_000,
        fecha=fecha,
        cargo_id=cargo_guarderia.id,
        usuario_id=usuario.id,
    )
    gasto_anulado = cobros_service.registrar_gasto_externo(
        db_session,
        empleado_externo_id=empleado.persona_id,
        descripcion="Gasto cargado dos veces",
        monto_centavos=4_000,
        fecha=fecha,
        cargo_id=cargo_guarderia.id,
        usuario_id=usuario.id,
    )
    cobros_service.anular_gasto_externo(
        db_session,
        gasto_id=gasto_anulado.id,
        motivo="Carga duplicada",
        usuario_id=usuario.id,
    )

    cobros_service.crear_cargo(
        db_session,
        persona_id=persona_deudora.id,
        concepto="Consulta impaga",
        total_centavos=7_000,
        tipo_servicio=TipoServicio.CONSULTA,
        usuario_id=usuario.id,
    )

    return EscenarioPanel(
        persona_id=persona.id,
        persona_deudora_id=persona_deudora.id,
        paciente_id=paciente.id,
        empleado_id=empleado.persona_id,
        usuario_id=usuario.id,
        cargo_guarderia_id=cargo_guarderia.id,
        cargo_consulta_id=cargo_consulta.id,
        fecha=fecha,
        desde=desde,
        hasta=hasta,
    )


def _login(client: TestClient, username: str) -> dict[str, str]:
    respuesta = client.post(
        "/api/auth/login", json={"username": username, "password": PASSWORD}
    )
    assert respuesta.status_code == 200
    return {"Authorization": f"Bearer {respuesta.json()['access_token']}"}


@pytest.fixture
def tokens(
    client: TestClient, db_session: Session, panel_escenario: EscenarioPanel
) -> dict[str, dict[str, str]]:
    for username, rol in (
        ("personal-panel", Rol.PERSONAL),
        ("veterinario-panel", Rol.VETERINARIO),
    ):
        identidad_service.crear_usuario(
            db_session,
            UsuarioCrear(username=username, password=PASSWORD, rol=rol),
        )
    return {
        "duenio": _login(client, "duenio-panel"),
        "personal": _login(client, "personal-panel"),
        "veterinario": _login(client, "veterinario-panel"),
    }
