"""Transiciones permitidas para los turnos médicos."""

from app.modules.clinica.models import EstadoTurno

TRANSICIONES: dict[EstadoTurno, frozenset[EstadoTurno]] = {
    EstadoTurno.PROGRAMADO: frozenset(
        {
            EstadoTurno.CONFIRMADO,
            EstadoTurno.CANCELADO,
            EstadoTurno.ATENDIDO,
            EstadoTurno.AUSENTE,
        }
    ),
    EstadoTurno.PENDIENTE_EXTERNO: frozenset(
        {
            EstadoTurno.PROGRAMADO,
            EstadoTurno.CONFIRMADO,
            EstadoTurno.CANCELADO,
        }
    ),
    EstadoTurno.CONFIRMADO: frozenset(
        {
            EstadoTurno.CANCELADO,
            EstadoTurno.ATENDIDO,
            EstadoTurno.AUSENTE,
        }
    ),
    EstadoTurno.ATENDIDO: frozenset(),
    EstadoTurno.CANCELADO: frozenset(),
    EstadoTurno.AUSENTE: frozenset(),
}


def puede_transicionar(actual: EstadoTurno, nuevo: EstadoTurno) -> bool:
    return nuevo in TRANSICIONES[actual]


def puede_reprogramar(estado: EstadoTurno) -> bool:
    return estado in {EstadoTurno.PROGRAMADO, EstadoTurno.CONFIRMADO}
