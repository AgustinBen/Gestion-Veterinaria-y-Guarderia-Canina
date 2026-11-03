import type { FiltrosPanel, PeriodoId } from '../tipos';
import estilos from '../panel.module.css';
import { calcularRango, PERIODOS } from './filtrosPanel';

type Props = {
  filtros: FiltrosPanel;
  onCambiar: (filtros: FiltrosPanel) => void;
};

/** Barra de filtros del panel. El estado vive en la URL (T-50). */
export function Filtros({ filtros, onCambiar }: Props) {
  function cambiarPeriodo(periodo: PeriodoId) {
    const rango =
      periodo === 'personalizado'
        ? { desde: filtros.desde, hasta: filtros.hasta }
        : calcularRango(periodo);

    onCambiar({ periodo, ...rango });
  }

  return (
    <section aria-label="Filtros del panel" className={estilos.filtros}>
      <div aria-label="Período" className={estilos.periodos} role="group">
        {PERIODOS.map((periodo) => (
          <button
            aria-pressed={filtros.periodo === periodo.id}
            className={estilos.periodo}
            key={periodo.id}
            onClick={() => cambiarPeriodo(periodo.id)}
            type="button"
          >
            {periodo.etiqueta}
          </button>
        ))}
      </div>

      {filtros.periodo === 'personalizado' ? (
        <div className={estilos.fechas}>
          <label>
            Desde
            <input
              onChange={(evento) =>
                onCambiar({
                  periodo: 'personalizado',
                  desde: evento.target.value,
                  hasta: filtros.hasta,
                })
              }
              type="date"
              value={filtros.desde}
            />
          </label>
          <label>
            Hasta
            <input
              onChange={(evento) =>
                onCambiar({
                  periodo: 'personalizado',
                  desde: filtros.desde,
                  hasta: evento.target.value,
                })
              }
              type="date"
              value={filtros.hasta}
            />
          </label>
        </div>
      ) : null}
    </section>
  );
}
