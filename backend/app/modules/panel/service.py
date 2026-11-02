"""Servicio del panel financiero del Dueño (T-46).

Criterio de caja en centavos:
- Ingresos: pagos menos reversos por fecha de pago.
- Egresos operativos: egresos no anulados del período.
- Gastos a externos: gastos no anulados, opcionalmente vinculados a un cargo.
- Rentabilidad neta: ingresos - egresos operativos - gastos a externos.
- Las deudas se informan aparte y nunca se restan de la rentabilidad (RN-40).

El panel no lee tablas de otros módulos: pide todo a `cobros.service` y a
`padron.service`.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.cobros import service as cobros_service
from app.modules.padron import service as padron_service
from app.modules.panel import repository, schemas

MOTIVO_MEDIO = (
    "Los gastos a externos no registran medio de pago: no se puede calcular "
    "la rentabilidad neta con el filtro por medio."
)
MOTIVO_SERVICIO = (
    "Los egresos operativos no se reparten entre servicios: se muestran como "
    "sin asignar."
)
DEUDORES_MOSTRADOS = 10


class PeriodoInvalido(ValueError):
    pass


class PersonaNoEncontrada(LookupError):
    pass


def _hoy_negocio() -> date:
    zona = ZoneInfo(get_settings().panel_zona_horaria)
    return datetime.now(timezone.utc).astimezone(zona).date()


def resolver_periodo(
    desde: date | None, hasta: date | None
) -> tuple[date, date]:
    """Período inclusivo en ambos extremos, con la zona horaria del negocio."""
    hoy = _hoy_negocio()
    inicio = desde if desde is not None else hoy.replace(day=1)
    fin = hasta if hasta is not None else hoy
    if inicio > fin:
        raise PeriodoInvalido("El período es inválido: desde es posterior a hasta")
    dias = (fin - inicio).days + 1
    maximo = get_settings().panel_rango_max_dias
    if dias > maximo:
        raise PeriodoInvalido(f"El rango máximo del panel es de {maximo} días")
    return inicio, fin


def _clave_texto(clave: object) -> str:
    if isinstance(clave, date):
        return clave.isoformat()
    return str(clave)


def resumen(
    db: Session,
    *,
    desde: date | None = None,
    hasta: date | None = None,
    servicio: str | None = None,
    medio: str | None = None,
    incluir_migracion: bool = False,
) -> schemas.ResumenPanelOut:
    inicio, fin = resolver_periodo(desde, hasta)

    ingresos = cobros_service.total_ingresos(
        db,
        desde=inicio,
        hasta=fin,
        tipo_servicio=servicio,
        medio=medio,
        incluir_migracion=incluir_migracion,
    )
    ingresos_migracion = cobros_service.total_ingresos(
        db,
        desde=inicio,
        hasta=fin,
        tipo_servicio="MIGRACION",
        medio=medio,
        incluir_migracion=True,
    )
    medio_pago_id = (
        (cobros_service.medio_pago_id_por_codigo(db, medio) or -1)
        if medio is not None
        else None
    )
    operativos = repository.total_egresos(
        db, desde=inicio, hasta=fin, medio_pago_id=medio_pago_id
    )
    if servicio is not None:
        externos = cobros_service.total_gastos_externos_por_tipo(
            db, desde=inicio, hasta=fin, tipo_servicio=servicio
        )
    else:
        externos = cobros_service.total_gastos_externos(
            db, desde=inicio, hasta=fin
        )

    if medio is not None:
        rentabilidad: int | None = None
        motivo: str | None = MOTIVO_MEDIO
        sin_asignar = operativos
    elif servicio is not None:
        rentabilidad = ingresos - externos
        motivo = MOTIVO_SERVICIO
        sin_asignar = operativos
    else:
        rentabilidad = ingresos - operativos - externos
        motivo = None
        sin_asignar = 0

    calidad = cobros_service.calidad_datos_cargos(db, desde=inicio, hasta=fin)
    return schemas.ResumenPanelOut(
        desde=inicio,
        hasta=fin,
        ingresos_centavos=ingresos,
        ingresos_migracion_centavos=ingresos_migracion,
        egresos_operativos_centavos=operativos,
        egresos_operativos_sin_asignar_centavos=sin_asignar,
        gastos_externos_centavos=externos,
        rentabilidad_neta_centavos=rentabilidad,
        rentabilidad_neta_motivo=motivo,
        calidad_datos=schemas.CalidadDatosOut(
            cargos_otro=calidad.otros,
            cargos_migrados=calidad.migrados,
            total_cargos=calidad.total,
        ),
    )


def serie(
    db: Session,
    *,
    desde: date | None = None,
    hasta: date | None = None,
    agrupar: str = "dia",
    servicio: str | None = None,
    medio: str | None = None,
    incluir_migracion: bool = False,
) -> schemas.SeriePanelOut:
    if agrupar not in {"dia", "mes"}:
        raise PeriodoInvalido("Agrupación inválida: use dia o mes")
    inicio, fin = resolver_periodo(desde, hasta)
    medio_pago_id = (
        (cobros_service.medio_pago_id_por_codigo(db, medio) or -1)
        if medio is not None
        else None
    )
    ingresos = cobros_service.ingresos_agregados(
        db,
        desde=inicio,
        hasta=fin,
        agrupar=agrupar,
        tipo_servicio=servicio,
        medio=medio,
        incluir_migracion=incluir_migracion,
    )
    egresos = repository.egresos_agregados(
        db,
        desde=inicio,
        hasta=fin,
        agrupar=agrupar,
        medio_pago_id=medio_pago_id,
    )

    acumulado: dict[str, dict[str, int]] = {}
    for fila in ingresos:
        acumulado.setdefault(fila.clave, {"ingresos": 0, "egresos": 0})[
            "ingresos"
        ] += fila.monto_centavos
    for fila in egresos:
        clave = _clave_texto(fila.clave)
        acumulado.setdefault(clave, {"ingresos": 0, "egresos": 0})["egresos"] += int(
            fila.monto_centavos
        )

    puntos = [
        schemas.PuntoSerieOut(
            clave=clave,
            ingresos_centavos=valores["ingresos"],
            egresos_operativos_centavos=valores["egresos"],
        )
        for clave, valores in sorted(acumulado.items())
    ]
    return schemas.SeriePanelOut(
        agrupar=agrupar, desde=inicio, hasta=fin, puntos=puntos
    )


def ingresos_por_servicio(
    db: Session,
    *,
    desde: date | None = None,
    hasta: date | None = None,
    servicio: str | None = None,
    medio: str | None = None,
    incluir_migracion: bool = False,
) -> list[schemas.IngresoPorServicioOut]:
    inicio, fin = resolver_periodo(desde, hasta)
    filas = cobros_service.ingresos_agregados(
        db,
        desde=inicio,
        hasta=fin,
        agrupar="tipo_servicio",
        tipo_servicio=servicio,
        medio=medio,
        incluir_migracion=incluir_migracion,
    )
    return [
        schemas.IngresoPorServicioOut(
            tipo_servicio=fila.clave, ingresos_centavos=fila.monto_centavos
        )
        for fila in filas
    ]


def ingresos_por_medio(
    db: Session,
    *,
    desde: date | None = None,
    hasta: date | None = None,
    servicio: str | None = None,
    medio: str | None = None,
    incluir_migracion: bool = False,
) -> list[schemas.IngresoPorMedioOut]:
    inicio, fin = resolver_periodo(desde, hasta)
    filas = cobros_service.ingresos_agregados(
        db,
        desde=inicio,
        hasta=fin,
        agrupar="medio",
        tipo_servicio=servicio,
        medio=medio,
        incluir_migracion=incluir_migracion,
    )
    return [
        schemas.IngresoPorMedioOut(medio=fila.clave, ingresos_centavos=fila.monto_centavos)
        for fila in filas
    ]


def deudas(db: Session) -> schemas.DeudasPanelOut:
    resumen_deudas = cobros_service.resumen_deudas_global(db)
    filas = cobros_service.listar_deudores(
        db,
        orden="monto",
        solo_migracion=False,
        limite=DEUDORES_MOSTRADOS,
        desplazamiento=0,
    )
    mayores = [
        schemas.MayorDeudorOut(
            persona_id=fila.persona.id,
            nombre=fila.persona.nombre,
            apellido=fila.persona.apellido,
            saldo_total_centavos=fila.saldo_total_centavos,
            migracion_centavos=fila.saldo_migracion_centavos,
            cantidad_cargos_pendientes=fila.cantidad_cargos_pendientes,
            deuda_mas_antigua=fila.deuda_mas_antigua,
        )
        for fila in filas
    ]
    return schemas.DeudasPanelOut(
        total_adeudado_centavos=resumen_deudas.total_centavos,
        cantidad_clientes=resumen_deudas.cantidad_clientes,
        deuda_migracion_centavos=resumen_deudas.migracion_centavos,
        mayores_deudores=mayores,
    )


def detalle_cliente(db: Session, persona_id: int) -> schemas.DetalleClienteOut:
    persona = padron_service.obtener_persona(db, persona_id)
    if persona is None:
        raise PersonaNoEncontrada("Persona no encontrada")
    filas = cobros_service.servicios_de_persona(db, persona_id)
    return schemas.DetalleClienteOut(
        persona_id=persona.id,
        nombre=persona.nombre,
        apellido=persona.apellido,
        servicios=[
            schemas.ServicioClienteOut(
                cargo_id=fila.cargo_id,
                tipo_servicio=fila.tipo_servicio,
                concepto=fila.concepto,
                total_centavos=fila.total_vigente_centavos,
                pagado_centavos=fila.pagado_centavos,
                saldo_centavos=fila.saldo_centavos,
                ajustes=fila.ajustes,
            )
            for fila in filas
        ],
    )
