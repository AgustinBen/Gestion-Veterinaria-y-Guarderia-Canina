"""Repositorio del módulo padrón."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.modules.padron import models


def crear_persona(db: Session, persona: models.Persona) -> models.Persona:
    db.add(persona)
    db.flush()
    db.refresh(persona)
    return persona


def obtener_persona(db: Session, persona_id: int) -> models.Persona | None:
    return db.get(models.Persona, persona_id)


def obtener_por_dni(
    db: Session, dni: str, *, excluir_id: int | None = None
) -> models.Persona | None:
    stmt = select(models.Persona).where(models.Persona.dni == dni)
    if excluir_id is not None:
        stmt = stmt.where(models.Persona.id != excluir_id)
    return db.execute(stmt).scalar_one_or_none()


def listar_personas(
    db: Session, *, excluir_id: int | None = None
) -> list[models.Persona]:
    stmt = select(models.Persona).order_by(
        models.Persona.apellido, models.Persona.nombre, models.Persona.id
    )
    if excluir_id is not None:
        stmt = stmt.where(models.Persona.id != excluir_id)
    return list(db.execute(stmt).scalars().all())


def buscar_personas(
    db: Session,
    *,
    texto: str | None = None,
    dni: str | None = None,
    telefono: str | None = None,
) -> list[models.Persona]:
    stmt = select(models.Persona)

    if dni is not None:
        stmt = stmt.where(models.Persona.dni == dni)

    if telefono is not None:
        personas_con_telefono = select(models.Telefono.persona_id).where(
            models.Telefono.numero_normalizado == telefono
        )
        stmt = stmt.where(models.Persona.id.in_(personas_con_telefono))

    if texto:
        patron = f"%{texto.strip()}%"
        digitos = re.sub(r"\D", "", texto)
        if len(digitos) > 10:
            digitos = digitos[-10:]
        condiciones = [
            models.Persona.nombre.ilike(patron),
            models.Persona.apellido.ilike(patron),
            models.Persona.dni.ilike(patron),
            models.Persona.id.in_(
                select(models.Titularidad.persona_id)
                .join(
                    models.Paciente,
                    models.Titularidad.paciente_id == models.Paciente.id,
                )
                .where(models.Paciente.nombre.ilike(patron))
            ),
        ]
        if digitos:
            condiciones.append(
                models.Persona.id.in_(
                    select(models.Telefono.persona_id).where(
                        models.Telefono.numero_normalizado.like(f"%{digitos}%")
                    )
                )
            )
        stmt = stmt.where(or_(*condiciones))

    return list(db.execute(stmt).scalars().all())


def crear_domicilio(db: Session, domicilio: models.Domicilio) -> models.Domicilio:
    db.add(domicilio)
    db.flush()
    db.refresh(domicilio)
    return domicilio


def actualizar_domicilio(
    db: Session, domicilio: models.Domicilio, datos: dict[str, Any]
) -> models.Domicilio:
    for campo, valor in datos.items():
        setattr(domicilio, campo, valor)
    db.flush()
    db.refresh(domicilio)
    return domicilio


def crear_telefono(db: Session, telefono: models.Telefono) -> models.Telefono:
    db.add(telefono)
    db.flush()
    db.refresh(telefono)
    return telefono


def reemplazar_telefonos(
    db: Session, persona_id: int, telefonos: list[tuple[str, str]]
) -> None:
    for existente in telefonos_de_persona(db, persona_id):
        db.delete(existente)
    db.flush()
    for numero_normalizado, numero_original in telefonos:
        crear_telefono(
            db,
            models.Telefono(
                persona_id=persona_id,
                numero_normalizado=numero_normalizado,
                numero_original=numero_original,
            ),
        )


def telefonos_de_persona(db: Session, persona_id: int) -> list[models.Telefono]:
    stmt = (
        select(models.Telefono)
        .where(models.Telefono.persona_id == persona_id)
        .order_by(models.Telefono.id)
    )
    return list(db.execute(stmt).scalars().all())


def listar_telefonos(db: Session) -> list[models.Telefono]:
    return list(db.execute(select(models.Telefono)).scalars().all())


def mascotas_de_persona(db: Session, persona_id: int) -> list[models.Paciente]:
    stmt = (
        select(models.Paciente)
        .join(
            models.Titularidad,
            models.Titularidad.paciente_id == models.Paciente.id,
        )
        .where(
            models.Titularidad.persona_id == persona_id,
            models.Titularidad.hasta.is_(None),
        )
        .order_by(models.Paciente.nombre, models.Paciente.id)
    )
    return list(db.execute(stmt).scalars().all())


def crear_paciente(db: Session, paciente: models.Paciente) -> models.Paciente:
    db.add(paciente)
    db.flush()
    db.refresh(paciente)
    return paciente


def obtener_paciente(db: Session, paciente_id: int) -> models.Paciente | None:
    return db.get(models.Paciente, paciente_id)


def buscar_pacientes(db: Session, *, texto: str | None = None) -> list[models.Paciente]:
    stmt = select(models.Paciente)

    if texto:
        patron = f"%{texto.strip()}%"
        tutores = (
            select(models.Titularidad.paciente_id)
            .join(
                models.Persona,
                models.Titularidad.persona_id == models.Persona.id,
            )
            .where(
                or_(
                    models.Persona.nombre.ilike(patron),
                    models.Persona.apellido.ilike(patron),
                )
            )
        )
        stmt = stmt.where(
            or_(
                models.Paciente.nombre.ilike(patron),
                models.Paciente.id.in_(tutores),
            )
        )

    stmt = stmt.order_by(models.Paciente.nombre, models.Paciente.id)
    return list(db.execute(stmt).scalars().all())


def crear_titularidad(
    db: Session, titularidad: models.Titularidad
) -> models.Titularidad:
    db.add(titularidad)
    db.flush()
    db.refresh(titularidad)
    return titularidad


def titulares_vigentes(db: Session, paciente_id: int) -> list[models.Titularidad]:
    stmt = (
        select(models.Titularidad)
        .where(
            models.Titularidad.paciente_id == paciente_id,
            models.Titularidad.hasta.is_(None),
        )
        .order_by(models.Titularidad.principal.desc(), models.Titularidad.desde)
    )
    return list(db.execute(stmt).scalars().all())


def obtener_tipo_contacto_por_nombre(
    db: Session, nombre: str
) -> models.TipoContacto | None:
    stmt = select(models.TipoContacto).where(models.TipoContacto.nombre == nombre)
    return db.execute(stmt).scalar_one_or_none()


def crear_empleado(db: Session, empleado: models.Empleado) -> models.Empleado:
    db.add(empleado)
    db.flush()
    db.refresh(empleado)
    return empleado


def obtener_empleado(db: Session, empleado_id: int) -> models.Empleado | None:
    return db.get(models.Empleado, empleado_id)


def listar_empleados(db: Session) -> list[models.Empleado]:
    return list(db.execute(select(models.Empleado)).scalars().all())


def listar_especies(db: Session) -> list[models.Especie]:
    return list(
        db.execute(select(models.Especie).order_by(models.Especie.nombre))
        .scalars()
        .all()
    )


def obtener_especie(db: Session, especie_id: int) -> models.Especie | None:
    return db.get(models.Especie, especie_id)


def listar_razas(db: Session, especie_id: int | None = None) -> list[models.Raza]:
    stmt = select(models.Raza).order_by(models.Raza.nombre, models.Raza.id)
    if especie_id is not None:
        stmt = stmt.where(models.Raza.especie_id == especie_id)
    return list(db.execute(stmt).scalars().all())


def obtener_raza(db: Session, raza_id: int) -> models.Raza | None:
    return db.get(models.Raza, raza_id)


def crear_raza(db: Session, raza: models.Raza) -> models.Raza:
    db.add(raza)
    db.flush()
    db.refresh(raza)
    return raza


def listar_tamanios(db: Session) -> list[models.Tamanio]:
    return list(
        db.execute(select(models.Tamanio).order_by(models.Tamanio.nombre))
        .scalars()
        .all()
    )


def obtener_tamanio(db: Session, tamanio_id: int) -> models.Tamanio | None:
    return db.get(models.Tamanio, tamanio_id)
