import type { Disponibilidad, Franja } from '../tipos';
import estilos from '../guarderia.module.css';

type Props = {
  franja: Franja;
  disponibilidad: Disponibilidad | null;
  seleccionada: boolean;
  onSeleccionar: () => void;
};

const ETIQUETAS: Record<Franja, string> = {
  DIA: 'Día',
  NOCHE: 'Noche',
};

export function ChipFranja({
  franja,
  disponibilidad,
  seleccionada,
  onSeleccionar,
}: Props) {
  if (!disponibilidad) {
    return (
      <p className={estilos.chipSinDatos}>
        {ETIQUETAS[franja]}: sin datos
      </p>
    );
  }

  const completo = disponibilidad.disponible <= 0;
  const estado = completo ? 'Completo' : 'Con lugar';
  const claseEstado = completo ? estilos.chipCompleto : estilos.chipConLugar;

  return (
    <div className={estilos.franja}>
      <button
        aria-expanded={seleccionada}
        aria-label={`${ETIQUETAS[franja]}: ${disponibilidad.ocupado} ocupadas de ${disponibilidad.publico}, ${estado}`}
        className={[estilos.chip, claseEstado, seleccionada ? estilos.chipSeleccionado : '']
          .filter(Boolean)
          .join(' ')}
        onClick={onSeleccionar}
        type="button"
      >
        <span className={estilos.chipNombre}>{franja === 'DIA' ? 'D' : 'N'}</span>
        <span className={estilos.chipLibres}>
          {disponibilidad.ocupado}/{disponibilidad.publico}
        </span>
        <span aria-hidden="true" className={estilos.chipIndicador}>
          {completo ? '×' : '✓'}
        </span>
        <strong className={estilos.chipEstado}>{estado}</strong>
      </button>
      {seleccionada ? (
        <dl aria-label={`Detalle ${ETIQUETAS[franja]}`} className={estilos.detalleChip}>
          <div>
            <dt>Ocupado</dt>
            <dd>{disponibilidad.ocupado}</dd>
          </div>
          <div>
            <dt>Plazas de emergencia</dt>
            <dd>{disponibilidad.plazas_emergencia}</dd>
          </div>
          <div>
            <dt>Habilitadas</dt>
            <dd>{disponibilidad.habilitadas}</dd>
          </div>
        </dl>
      ) : null}
    </div>
  );
}
