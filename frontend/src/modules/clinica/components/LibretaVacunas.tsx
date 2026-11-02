import type { EstadoVacuna, LibretaVacunasItem } from '../tipos';
import estilos from '../clinica.module.css';

const ETIQUETA_ESTADO: Record<EstadoVacuna, string> = {
  VIGENTE: 'Vigente',
  POR_VENCER: 'Por vencer',
  VENCIDA: 'Vencida',
};

const CLASE_ESTADO: Record<EstadoVacuna, string> = {
  VIGENTE: estilos.vacunaVigente ?? '',
  POR_VENCER: estilos.vacunaPorVencer ?? '',
  VENCIDA: estilos.vacunaVencida ?? '',
};

type Props = {
  items: LibretaVacunasItem[];
};

export function LibretaVacunas({ items }: Props) {
  return (
    <section className={estilos.panel} aria-labelledby="libreta-vacunas-titulo">
      <div className={estilos.panelCabecera}>
        <h3 className={estilos.panelTitulo} id="libreta-vacunas-titulo">
          Libreta de vacunas
        </h3>
        <span className={estilos.etiqueta}>{items.length} aplicadas</span>
      </div>

      {items.length === 0 ? (
        <p className={estilos.vacio}>
          Todavía no hay vacunas registradas para esta mascota.
        </p>
      ) : (
        <ul className={estilos.libreta}>
          {items.map((item) => (
            <li className={estilos.libretaItem} key={item.atencion_id}>
              <div className={estilos.tarjetaCabecera}>
                <strong>{item.nombre_vacuna}</strong>
                <span
                  className={`${estilos.estado} ${CLASE_ESTADO[item.estado]}`.trim()}
                >
                  {ETIQUETA_ESTADO[item.estado]}
                </span>
              </div>
              <div className={estilos.meta}>
                <span>
                  Aplicada: <strong>{item.fecha_aplicacion}</strong>
                </span>
                {item.lote ? (
                  <span>
                    Lote: <strong>{item.lote}</strong>
                  </span>
                ) : null}
                <span>
                  Próxima dosis:{' '}
                  <strong>{item.proxima_dosis ?? 'sin fecha'}</strong>
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
