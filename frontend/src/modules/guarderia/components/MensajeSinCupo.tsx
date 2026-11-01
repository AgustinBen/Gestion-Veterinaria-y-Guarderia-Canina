import { Link } from 'react-router-dom';

import { formatoFechaReserva } from '../fechas';
import type { ErrorReserva } from '../tipos';
import estilos from '../guarderia.module.css';

type Props = {
  error: ErrorReserva;
  nombresMascotas: ReadonlyMap<number, string>;
};

const ETIQUETAS_FRANJA = {
  DIA: 'día',
  NOCHE: 'noche',
} as const;

export function MensajeSinCupo({ error, nombresMascotas }: Props) {
  if (error.codigo === 'YA_RESERVADO') {
    const nombres = [
      ...new Set(
        error.ocupaciones_existentes.map(
          (ocupacion) =>
            nombresMascotas.get(ocupacion.paciente_id) ?? 'una mascota seleccionada',
        ),
      ),
    ];

    return (
      <div className={estilos.mensajeConflicto} role="alert">
        <p>Ya hay una reserva para {nombres.join(' y ')} en ese tramo.</p>
        <Link to="/guarderia/calendario">Ver calendario</Link>
      </div>
    );
  }

  const franjas = error.franjas_sin_lugar.map(
    (franja) => `${formatoFechaReserva(franja.fecha)} (${ETIQUETAS_FRANJA[franja.franja]})`,
  );

  return (
    <div className={estilos.mensajeConflicto} role="alert">
      <p>
        {franjas.length > 0
          ? `No hay lugar el ${franjas.join(' y el ')}.`
          : 'No hay lugar para ese tramo.'}
      </p>
      <Link to="/guarderia/calendario">Ver calendario</Link>
    </div>
  );
}
