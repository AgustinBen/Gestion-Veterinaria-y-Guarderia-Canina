"""Seeds del módulo padrón."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.modules.padron import models


def sembrar_especies_tamanios_tipo_contacto(db: Session) -> None:
    if db.query(models.Especie).count() == 0:
        db.add_all(
            [
                models.Especie(nombre="Perro"),
                models.Especie(nombre="Gato"),
            ]
        )
    if db.query(models.Tamanio).count() == 0:
        db.add_all(
            [
                models.Tamanio(nombre="Chico"),
                models.Tamanio(nombre="Mediano"),
                models.Tamanio(nombre="Grande"),
            ]
        )
    if db.query(models.TipoContacto).count() == 0:
        db.add_all(
            [
                models.TipoContacto(nombre="TITULAR"),
                models.TipoContacto(nombre="CONTACTO ALTERNATIVO"),
            ]
        )
    db.flush()
