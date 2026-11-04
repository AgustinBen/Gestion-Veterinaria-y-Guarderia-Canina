import estilos from './ui.module.css';

type Props = {
  ariaLabel: string;
  pagina: number;
  cantidadPaginas: number;
  onCambiarPagina: (pagina: number) => void;
};

/** Paginado cliente-side compartido por los listados de la aplicación. */
export function Paginacion({
  ariaLabel,
  pagina,
  cantidadPaginas,
  onCambiarPagina,
}: Props) {
  if (cantidadPaginas <= 1) {
    return null;
  }

  return (
    <nav className={estilos.paginacion} aria-label={ariaLabel}>
      <div className={estilos.controlesPaginacion}>
        <button
          aria-label="Página anterior"
          className={estilos.botonPaginacion}
          disabled={pagina === 1}
          onClick={() => onCambiarPagina(pagina - 1)}
          type="button"
        >
          Anterior
        </button>
        <span aria-current="page" className={estilos.indicadorPagina}>
          Página {pagina} de {cantidadPaginas}
        </span>
        <button
          aria-label="Página siguiente"
          className={estilos.botonPaginacion}
          disabled={pagina === cantidadPaginas}
          onClick={() => onCambiarPagina(pagina + 1)}
          type="button"
        >
          Siguiente
        </button>
      </div>
    </nav>
  );
}
