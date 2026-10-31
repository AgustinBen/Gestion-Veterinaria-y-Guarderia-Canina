from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.guarderia.franjas import Franja
from app.modules.guarderia.models import Ocupacion


def contar_ocupacion(db: Session, fecha: date, franja: Franja) -> int:
    stmt = select(func.count(Ocupacion.id)).where(
        Ocupacion.fecha == fecha,
        Ocupacion.franja == franja,
    )
    return db.execute(stmt).scalar_one()
