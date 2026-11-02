"""Repositorio del módulo cobros. Sin funciones para modificar/borrar cargo, ajuste_precio o pago."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, aliased

from app.modules.cobros import models


def total_vigente(db: Session, cargo_id: int) -> int:
    ultimo = db.execute(
        select(models.AjustePrecio.precio_nuevo)
        .where(models.AjustePrecio.cargo_id == cargo_id)
        .order_by(models.AjustePrecio.created_at.desc(), models.AjustePrecio.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    if ultimo is not None:
        return int(ultimo)

    cargo = db.get(models.Cargo, cargo_id)
    if cargo is None:
        raise ValueError("Cargo no encontrado")
    return int(cargo.total_inicial)


def total_senas(db: Session, cargo_id: int) -> int:
    pago_sena = aliased(models.Pago)
    reverso = aliased(models.Pago)
    stmt = select(
        func.coalesce(func.sum(pago_sena.monto), 0)
    ).where(
        pago_sena.cargo_id == cargo_id,
        pago_sena.es_sena.is_(True),
        pago_sena.tipo == models.TipoPago.PAGO,
        ~select(reverso.id)
        .where(reverso.pago_revertido_id == pago_sena.id)
        .exists(),
    )
    return int(db.execute(stmt).scalar_one())


def total_pagado(db: Session, cargo_id: int) -> int:
    pagos = db.execute(
        select(func.coalesce(func.sum(models.Pago.monto), 0)).where(
            models.Pago.cargo_id == cargo_id, models.Pago.tipo == models.TipoPago.PAGO
        )
    ).scalar_one()
    reversos = db.execute(
        select(func.coalesce(func.sum(models.Pago.monto), 0)).where(
            models.Pago.cargo_id == cargo_id, models.Pago.tipo == models.TipoPago.REVERSO
        )
    ).scalar_one()
    return int(pagos) - int(reversos)


def saldo(db: Session, cargo_id: int) -> int:
    return total_vigente(db, cargo_id) - total_pagado(db, cargo_id)


def _cargos_con_saldo() -> Any:
    ultimo_ajuste = (
        select(models.AjustePrecio.precio_nuevo)
        .where(models.AjustePrecio.cargo_id == models.Cargo.id)
        .order_by(models.AjustePrecio.created_at.desc(), models.AjustePrecio.id.desc())
        .limit(1)
        .scalar_subquery()
    )
    total_vigente_expr = func.coalesce(ultimo_ajuste, models.Cargo.total_inicial)
    pagos_netos_expr = func.coalesce(
        func.sum(
            case(
                (models.Pago.tipo == models.TipoPago.PAGO, models.Pago.monto),
                else_=0,
            )
        ),
        0,
    ) - func.coalesce(
        func.sum(
            case(
                (models.Pago.tipo == models.TipoPago.REVERSO, models.Pago.monto),
                else_=0,
            )
        ),
        0,
    )
    return (
        select(
            models.Cargo.id.label("cargo_id"),
            models.Cargo.persona_id.label("persona_id"),
            models.Cargo.origen.label("origen"),
            models.Cargo.created_at.label("created_at"),
            (total_vigente_expr - pagos_netos_expr).label("saldo"),
        )
        .outerjoin(models.Pago, models.Pago.cargo_id == models.Cargo.id)
        .group_by(
            models.Cargo.id,
            models.Cargo.persona_id,
            models.Cargo.origen,
            models.Cargo.created_at,
            models.Cargo.total_inicial,
        )
        .subquery()
    )


def listar_deudores(
    db: Session,
    *,
    orden: str,
    solo_migracion: bool,
    limite: int,
    desplazamiento: int,
) -> list[Any]:
    cargos = _cargos_con_saldo()
    pendientes = select(cargos).where(cargos.c.saldo > 0).subquery()
    migrado = case(
        (pendientes.c.origen == models.OrigenCargo.MIGRACION, pendientes.c.saldo),
        else_=0,
    )
    stmt = select(
        pendientes.c.persona_id,
        func.sum(pendientes.c.saldo).label("saldo_total_centavos"),
        func.count(pendientes.c.cargo_id).label("cantidad_cargos_pendientes"),
        func.min(pendientes.c.created_at).label("deuda_mas_antigua"),
        func.sum(migrado).label("saldo_migracion_centavos"),
    ).group_by(pendientes.c.persona_id)
    if solo_migracion:
        stmt = stmt.having(func.sum(migrado) > 0)
    if orden == "antiguedad":
        stmt = stmt.order_by(
            func.min(pendientes.c.created_at).asc(), pendientes.c.persona_id
        )
    else:
        stmt = stmt.order_by(
            func.sum(pendientes.c.saldo).desc(), pendientes.c.persona_id
        )
    stmt = stmt.limit(limite).offset(desplazamiento)
    return list(db.execute(stmt).all())


def resumen_deuda(db: Session, persona_id: int) -> Any:
    cargos = _cargos_con_saldo()
    pendientes = select(cargos).where(
        cargos.c.persona_id == persona_id, cargos.c.saldo > 0
    ).subquery()
    stmt = select(
        func.coalesce(func.sum(pendientes.c.saldo), 0).label("saldo_total_centavos"),
        func.count(pendientes.c.cargo_id).label("cargos_pendientes"),
        func.min(pendientes.c.created_at).label("deuda_mas_antigua"),
        func.coalesce(
            func.sum(
                case(
                    (
                        pendientes.c.origen == models.OrigenCargo.MIGRACION,
                        pendientes.c.saldo,
                    ),
                    else_=0,
                )
            ),
            0,
        ).label("saldo_migracion_centavos"),
    )
    return db.execute(stmt).one()


def crear_ajuste(
    db: Session,
    *,
    cargo_id: int,
    precio_anterior: int,
    precio_nuevo: int,
    motivo: str,
    usuario_id: int,
) -> models.AjustePrecio:
    ajuste = models.AjustePrecio(
        cargo_id=cargo_id,
        precio_anterior=precio_anterior,
        precio_nuevo=precio_nuevo,
        motivo=motivo,
        usuario_id=usuario_id,
    )
    db.add(ajuste)
    db.flush()
    return ajuste


def ajustes_de_cargo(db: Session, cargo_id: int) -> list[models.AjustePrecio]:
    return list(
        db.execute(
            select(models.AjustePrecio)
            .where(models.AjustePrecio.cargo_id == cargo_id)
            .order_by(models.AjustePrecio.created_at.asc(), models.AjustePrecio.id.asc())
        ).scalars().all()
    )


def obtener_cargo(db: Session, cargo_id: int) -> models.Cargo | None:
    return db.get(models.Cargo, cargo_id)


def obtener_pago(db: Session, pago_id: int) -> models.Pago | None:
    return db.get(models.Pago, pago_id)


def obtener_medio_pago_por_codigo(db: Session, codigo: str) -> models.MedioPago | None:
    return db.execute(
        select(models.MedioPago).where(models.MedioPago.codigo == codigo.upper())
    ).scalar_one_or_none()


def obtener_medio_pago(db: Session, medio_pago_id: int) -> models.MedioPago | None:
    return db.get(models.MedioPago, medio_pago_id)


def listar_medios_pago_activos(db: Session) -> list[models.MedioPago]:
    return list(
        db.execute(
            select(models.MedioPago)
            .where(models.MedioPago.activo.is_(True))
            .order_by(models.MedioPago.id)
        ).scalars().all()
    )


def obtener_pago_por_clave_idempotencia(db: Session, clave: str) -> models.Pago | None:
    return db.execute(
        select(models.Pago).where(models.Pago.clave_idempotencia == clave)
    ).scalar_one_or_none()


def tiene_reverso(db: Session, pago_id: int) -> bool:
    existe = db.execute(
        select(models.Pago.id).where(
            models.Pago.tipo == models.TipoPago.REVERSO,
            models.Pago.pago_revertido_id == pago_id,
        )
    ).scalar_one_or_none()
    return existe is not None


def pagos_de_cargo(db: Session, cargo_id: int) -> list[models.Pago]:
    return list(
        db.execute(select(models.Pago).where(models.Pago.cargo_id == cargo_id).order_by(models.Pago.id)).scalars().all()
    )


def cargos_de_persona(db: Session, persona_id: int) -> list[models.Cargo]:
    return list(
        db.execute(select(models.Cargo).where(models.Cargo.persona_id == persona_id).order_by(models.Cargo.id)).scalars().all()
    )


def cargos_de_paciente(db: Session, paciente_id: int) -> list[models.Cargo]:
    return list(
        db.execute(select(models.Cargo).where(models.Cargo.paciente_id == paciente_id).order_by(models.Cargo.id)).scalars().all()
    )


def crear_gasto_externo(
    db: Session,
    *,
    empleado_id: int,
    descripcion: str,
    monto: int,
    fecha: date,
    cargo_id: int | None,
    pago_id: int | None,
    registrado_por: int,
) -> models.GastoExterno:
    gasto = models.GastoExterno(
        empleado_id=empleado_id,
        descripcion=descripcion,
        monto=monto,
        fecha=fecha,
        cargo_id=cargo_id,
        pago_id=pago_id,
        registrado_por=registrado_por,
    )
    db.add(gasto)
    db.flush()
    return gasto


def obtener_gasto_externo(db: Session, gasto_id: int) -> models.GastoExterno | None:
    return db.get(models.GastoExterno, gasto_id)


def _filtros_gastos(
    *,
    desde: date | None,
    hasta: date | None,
    empleado_id: int | None,
    cargo_id: int | None,
) -> list[Any]:
    filtros: list[Any] = []
    if desde is not None:
        filtros.append(models.GastoExterno.fecha >= desde)
    if hasta is not None:
        filtros.append(models.GastoExterno.fecha <= hasta)
    if empleado_id is not None:
        filtros.append(models.GastoExterno.empleado_id == empleado_id)
    if cargo_id is not None:
        filtros.append(models.GastoExterno.cargo_id == cargo_id)
    return filtros


def listar_gastos_externos(
    db: Session,
    *,
    desde: date | None,
    hasta: date | None,
    empleado_id: int | None,
    cargo_id: int | None,
    limite: int,
    desplazamiento: int,
) -> list[models.GastoExterno]:
    stmt = (
        select(models.GastoExterno)
        .where(
            *_filtros_gastos(
                desde=desde,
                hasta=hasta,
                empleado_id=empleado_id,
                cargo_id=cargo_id,
            )
        )
        .order_by(models.GastoExterno.fecha.desc(), models.GastoExterno.id.desc())
        .limit(limite)
        .offset(desplazamiento)
    )
    return list(db.execute(stmt).scalars().all())


def total_gastos_externos(
    db: Session,
    *,
    desde: date | None,
    hasta: date | None,
    empleado_id: int | None,
    cargo_id: int | None,
) -> int:
    stmt = select(func.coalesce(func.sum(models.GastoExterno.monto), 0)).where(
        models.GastoExterno.anulado_en.is_(None),
        *_filtros_gastos(
            desde=desde,
            hasta=hasta,
            empleado_id=empleado_id,
            cargo_id=cargo_id,
        ),
    )
    return int(db.execute(stmt).scalar_one())


# --- Agregados para el panel financiero (T-38 / T-46) -----------------------


def _neto_pago() -> Any:
    """Criterio de caja: los pagos suman y los reversos restan."""
    return case(
        (models.Pago.tipo == models.TipoPago.PAGO, models.Pago.monto),
        else_=-models.Pago.monto,
    )


def _filtros_ingresos(
    *,
    desde: date,
    hasta: date,
    tipo_servicio: str | None,
    medio: str | None,
    incluir_migracion: bool,
) -> list[Any]:
    filtros: list[Any] = [
        models.Pago.fecha >= desde,
        models.Pago.fecha <= hasta,
    ]
    if tipo_servicio is not None:
        filtros.append(models.Cargo.tipo_servicio == tipo_servicio)
    if medio is not None:
        filtros.append(models.MedioPago.codigo == medio.upper())
    if not incluir_migracion:
        filtros.append(models.Cargo.tipo_servicio != models.TipoServicio.MIGRACION)
        filtros.append(models.Cargo.origen != models.OrigenCargo.MIGRACION)
    return filtros


def _consulta_ingresos(
    *,
    desde: date,
    hasta: date,
    tipo_servicio: str | None,
    medio: str | None,
    incluir_migracion: bool,
) -> Any:
    return (
        select(func.coalesce(func.sum(_neto_pago()), 0).label("monto_centavos"))
        .join(models.Cargo, models.Cargo.id == models.Pago.cargo_id)
        .join(models.MedioPago, models.MedioPago.id == models.Pago.medio_pago_id)
        .where(
            *_filtros_ingresos(
                desde=desde,
                hasta=hasta,
                tipo_servicio=tipo_servicio,
                medio=medio,
                incluir_migracion=incluir_migracion,
            )
        )
    )


def total_ingresos(
    db: Session,
    *,
    desde: date,
    hasta: date,
    tipo_servicio: str | None,
    medio: str | None,
    incluir_migracion: bool,
) -> int:
    stmt = _consulta_ingresos(
        desde=desde,
        hasta=hasta,
        tipo_servicio=tipo_servicio,
        medio=medio,
        incluir_migracion=incluir_migracion,
    )
    return int(db.execute(stmt).scalar_one())


def ingresos_agregados(
    db: Session,
    *,
    desde: date,
    hasta: date,
    agrupar: str,
    tipo_servicio: str | None,
    medio: str | None,
    incluir_migracion: bool,
) -> list[Any]:
    """Ingresos netos agrupados por día, mes, medio o tipo de servicio."""
    clave: Any
    grupo: Any
    if agrupar == "dia":
        clave = models.Pago.fecha.label("clave")
        grupo = models.Pago.fecha
    elif agrupar == "mes":
        clave = func.strftime("%Y-%m", models.Pago.fecha).label("clave")
        grupo = func.strftime("%Y-%m", models.Pago.fecha)
    elif agrupar == "medio":
        clave = models.MedioPago.codigo.label("clave")
        grupo = models.MedioPago.codigo
    elif agrupar == "tipo_servicio":
        clave = models.Cargo.tipo_servicio.label("clave")
        grupo = models.Cargo.tipo_servicio
    else:  # pragma: no cover - el servicio valida antes
        raise ValueError(f"Agrupación inválida: {agrupar}")

    stmt = (
        select(clave, func.coalesce(func.sum(_neto_pago()), 0).label("monto_centavos"))
        .join(models.Cargo, models.Cargo.id == models.Pago.cargo_id)
        .join(models.MedioPago, models.MedioPago.id == models.Pago.medio_pago_id)
        .where(
            *_filtros_ingresos(
                desde=desde,
                hasta=hasta,
                tipo_servicio=tipo_servicio,
                medio=medio,
                incluir_migracion=incluir_migracion,
            )
        )
        .group_by(grupo)
        .order_by(grupo)
    )
    return list(db.execute(stmt).all())


def calidad_datos_cargos(db: Session, *, desde: date, hasta: date) -> Any:
    """Cuenta los cargos del período que quedaron sin clasificar."""
    desde_dt = datetime.combine(desde, time.min)
    hasta_dt = datetime.combine(hasta + timedelta(days=1), time.min)
    stmt = select(
        func.coalesce(
            func.sum(case((models.Cargo.tipo_servicio == models.TipoServicio.OTRO, 1), else_=0)),
            0,
        ).label("otros"),
        func.coalesce(
            func.sum(
                case((models.Cargo.tipo_servicio == models.TipoServicio.MIGRACION, 1), else_=0)
            ),
            0,
        ).label("migrados"),
        func.count(models.Cargo.id).label("total"),
    ).where(
        models.Cargo.created_at >= desde_dt,
        models.Cargo.created_at < hasta_dt,
    )
    return db.execute(stmt).one()


def gastos_externos_por_tipo_servicio(
    db: Session, *, desde: date, hasta: date
) -> list[Any]:
    stmt = (
        select(
            models.Cargo.tipo_servicio.label("clave"),
            func.coalesce(func.sum(models.GastoExterno.monto), 0).label("monto_centavos"),
        )
        .join(models.Cargo, models.Cargo.id == models.GastoExterno.cargo_id)
        .where(
            models.GastoExterno.anulado_en.is_(None),
            models.GastoExterno.fecha >= desde,
            models.GastoExterno.fecha <= hasta,
        )
        .group_by(models.Cargo.tipo_servicio)
        .order_by(models.Cargo.tipo_servicio)
    )
    return list(db.execute(stmt).all())


def total_gastos_externos_por_tipo(
    db: Session, *, desde: date, hasta: date, tipo_servicio: str
) -> int:
    stmt = (
        select(func.coalesce(func.sum(models.GastoExterno.monto), 0))
        .join(models.Cargo, models.Cargo.id == models.GastoExterno.cargo_id)
        .where(
            models.GastoExterno.anulado_en.is_(None),
            models.GastoExterno.fecha >= desde,
            models.GastoExterno.fecha <= hasta,
            models.Cargo.tipo_servicio == tipo_servicio,
        )
    )
    return int(db.execute(stmt).scalar_one())


def resumen_deudas_global(db: Session) -> Any:
    cargos = _cargos_con_saldo()
    pendientes = select(cargos).where(cargos.c.saldo > 0).subquery()
    stmt = select(
        func.coalesce(func.sum(pendientes.c.saldo), 0).label("total_centavos"),
        func.count(func.distinct(pendientes.c.persona_id)).label("cantidad_clientes"),
        func.coalesce(
            func.sum(
                case(
                    (
                        pendientes.c.origen == models.OrigenCargo.MIGRACION,
                        pendientes.c.saldo,
                    ),
                    else_=0,
                )
            ),
            0,
        ).label("migracion_centavos"),
    )
    return db.execute(stmt).one()


def servicios_de_persona(db: Session, persona_id: int) -> list[Any]:
    ultimo_ajuste = (
        select(models.AjustePrecio.precio_nuevo)
        .where(models.AjustePrecio.cargo_id == models.Cargo.id)
        .order_by(models.AjustePrecio.created_at.desc(), models.AjustePrecio.id.desc())
        .limit(1)
        .scalar_subquery()
    )
    total_vigente_expr = func.coalesce(ultimo_ajuste, models.Cargo.total_inicial)
    pagado_expr = (
        select(
            func.coalesce(
                func.sum(
                    case(
                        (models.Pago.tipo == models.TipoPago.PAGO, models.Pago.monto),
                        else_=-models.Pago.monto,
                    )
                ),
                0,
            )
        )
        .where(models.Pago.cargo_id == models.Cargo.id)
        .scalar_subquery()
    )
    ajustes_expr = (
        select(func.count(models.AjustePrecio.id))
        .where(models.AjustePrecio.cargo_id == models.Cargo.id)
        .scalar_subquery()
    )
    stmt = (
        select(
            models.Cargo.id.label("cargo_id"),
            models.Cargo.tipo_servicio.label("tipo_servicio"),
            models.Cargo.concepto.label("concepto"),
            total_vigente_expr.label("total_vigente_centavos"),
            pagado_expr.label("pagado_centavos"),
            (total_vigente_expr - pagado_expr).label("saldo_centavos"),
            ajustes_expr.label("ajustes"),
        )
        .where(models.Cargo.persona_id == persona_id)
        .order_by(models.Cargo.id)
    )
    return list(db.execute(stmt).all())

