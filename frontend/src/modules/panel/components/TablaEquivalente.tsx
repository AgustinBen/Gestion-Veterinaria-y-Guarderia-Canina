import estilos from '../panel.module.css';

export type FilaTabla = {
  etiqueta: string;
  valores: string[];
};

type Props = {
  titulo: string;
  columnas: string[];
  filas: FilaTabla[];
  vacio?: string;
};

/** Tabla con los mismos datos del gráfico: el gráfico no es la única fuente. */
export function TablaEquivalente({
  titulo,
  columnas,
  filas,
  vacio = 'Sin datos para el período.',
}: Props) {
  return (
    <div className={estilos.tablaContenedor}>
      <table className={estilos.tabla}>
        <caption>Datos de {titulo}</caption>
        <thead>
          <tr>
            {columnas.map((columna) => (
              <th key={columna} scope="col">
                {columna}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {filas.length === 0 ? (
            <tr>
              <td colSpan={columnas.length}>{vacio}</td>
            </tr>
          ) : (
            filas.map((fila) => (
              <tr key={fila.etiqueta}>
                <th scope="row">{fila.etiqueta}</th>
                {fila.valores.map((valor, indice) => (
                  <td key={`${fila.etiqueta}-${indice}`}>{valor}</td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
