"""Detección de duplicados del padrón (RN-02 y RN-06)."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from sqlalchemy.orm import Session

from app.modules.padron import models, repository, schemas
from app.modules.padron.normalizacion import normalizar_texto


@dataclass(frozen=True)
class Coincidencia:
    """Coincidencia detectada antes de crear o editar una persona."""

    persona: models.Persona
    motivo: str
    mascotas: list[str]


def nombre_parecido(primero: str, segundo: str, umbral: float) -> bool:
    """Igualdad normalizada o similitud mayor o igual al umbral configurado."""
    if primero == segundo:
        return True
    return SequenceMatcher(None, primero, segundo).ratio() >= umbral


def _nombre_completo(persona: models.Persona) -> str:
    return normalizar_texto(f"{persona.nombre} {persona.apellido}")


def detectar_coincidencias(
    db: Session,
    nombre: str,
    apellido: str,
    telefonos_normalizados: list[str],
    umbral: float,
    *,
    excluir_id: int | None = None,
) -> list[Coincidencia]:
    """Lista personas con teléfono repetido o nombre parecido.

    No fusiona ni modifica nada: solo informa para que la confirmación sea
    explícita (RN-06).
    """
    buscado = normalizar_texto(f"{nombre} {apellido}")
    numeros = set(telefonos_normalizados)

    telefonos_por_persona: dict[int, set[str]] = {}
    for telefono in repository.listar_telefonos(db):
        telefonos_por_persona.setdefault(telefono.persona_id, set()).add(
            telefono.numero_normalizado
        )

    coincidencias: list[Coincidencia] = []
    for persona in repository.listar_personas(db, excluir_id=excluir_id):
        mismo_telefono = bool(numeros & telefonos_por_persona.get(persona.id, set()))
        mismo_nombre = nombre_parecido(buscado, _nombre_completo(persona), umbral)
        if not mismo_telefono and not mismo_nombre:
            continue
        motivo = "TELEFONO" if mismo_telefono else "NOMBRE"
        mascotas = [
            paciente.nombre
            for paciente in repository.mascotas_de_persona(db, persona.id)
        ]
        coincidencias.append(
            Coincidencia(persona=persona, motivo=motivo, mascotas=mascotas)
        )
    return coincidencias


def a_coincidencia_out(
    db: Session, coincidencia: Coincidencia
) -> schemas.CoincidenciaOut:
    """Convierte una coincidencia interna al DTO que devuelve la API."""
    return schemas.CoincidenciaOut(
        persona=schemas.PersonaResumen(
            id=coincidencia.persona.id,
            nombre=coincidencia.persona.nombre,
            apellido=coincidencia.persona.apellido,
            dni=coincidencia.persona.dni,
            dni_pendiente=coincidencia.persona.dni is None,
            telefonos=[
                telefono.numero_normalizado
                for telefono in repository.telefonos_de_persona(db, coincidencia.persona.id)
            ],
        ),
        motivo=coincidencia.motivo,
        mascotas=coincidencia.mascotas,
    )
