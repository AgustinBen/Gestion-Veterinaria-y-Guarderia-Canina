import { formatearDinero } from '../../../core/formatos/dinero';
import estilos from '../panel.module.css';
import { TablaEquivalente } from './TablaEquivalente';

export type PorcionDona = {
  etiqueta: string;
  valor: number;
};

type Props = {
  titulo: string;
  datos: PorcionDona[];
};

const COLORES = [
  'var(--dona-1)',
  'var(--dona-2)',
  'var(--dona-3)',
  'var(--dona-4)',
  'var(--dona-5)',
  'var(--dona-6)',
];

/**
 * Dona de participaciones con CSS puro (`conic-gradient`), sin SVG ni
 * animación (T-50). La leyenda y la tabla equivalente conservan los datos.
 */
export function GraficoDona({ titulo, datos }: Props) {
  const total = datos.reduce((suma, item) => suma + item.valor, 0);
  const paradas: string[] = [];
  let acumulado = 0;

  if (total > 0) {
    datos.forEach((item, indice) => {
      const inicio = (acumulado / total) * 100;
      acumulado += item.valor;
      const fin = (acumulado / total) * 100;

      paradas.push(`${COLORES[indice % COLORES.length]} ${inicio}% ${fin}%`);
    });
  }
  const resumen = datos
    .map((item) => `${item.etiqueta}: ${formatearDinero(item.valor)}`)
    .join('; ');

  return (
    <figure className={estilos.grafico}>
      <figcaption className={estilos.graficoTitulo}>{titulo}</figcaption>

      {total <= 0 ? (
        <p className={estilos.textoSuave}>Sin datos para el período.</p>
      ) : (
        <div className={estilos.donaContenido}>
          <div
            aria-label={`${titulo}. ${resumen}`}
            className={estilos.donaCss}
            role="img"
            style={{ background: `conic-gradient(${paradas.join(', ')})` }}
          />

          <ul aria-label={`Referencias de ${titulo}`} className={estilos.leyenda}>
            {datos.map((item, indice) => (
              <li key={item.etiqueta}>
                <span
                  aria-hidden="true"
                  className={estilos.muestra}
                  style={{ background: COLORES[indice % COLORES.length] }}
                />
                {item.etiqueta}: {formatearDinero(item.valor)}
              </li>
            ))}
          </ul>
        </div>
      )}

      <TablaEquivalente
        columnas={['Categoría', 'Ingresos']}
        filas={datos.map((item) => ({
          etiqueta: item.etiqueta,
          valores: [formatearDinero(item.valor)],
        }))}
        titulo={titulo}
      />
    </figure>
  );
}
