"""Repositorio mínimo para padrón."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.modules.padron import models


def crear_persona(db: Session, persona: models.Persona) -> models.Persona:
    db.add(persona)
    db.flush()
    db.refresh(persona)
    return persona


def obtener_persona(db: Session, persona_id: int) -> models.Persona | None:
    return db.get(models.Persona, persona_id)


def crear_paciente(db: Session, paciente: models.Paciente) -> models.Paciente:
    db.add(paciente)
    db.flush()
    db.refresh(paciente)
    return paciente


def obtener_paciente(db: Session, paciente_id: int) -> models.Paciente | None:
    return db.get(models.Paciente, paciente_id)
