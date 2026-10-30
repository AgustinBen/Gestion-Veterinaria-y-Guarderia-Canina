import { useEffect, useId, type ReactNode } from 'react';

import estilos from './ui.module.css';

type Props = {
  abierto: boolean;
  titulo: string;
  descripcion?: ReactNode;
  onCerrar: () => void;
  bloquearCierre?: boolean;
  children: ReactNode;
  pie?: ReactNode;
};

export function DialogoConfirmacion({
  abierto,
  titulo,
  descripcion,
  onCerrar,
  bloquearCierre = false,
  children,
  pie,
}: Props) {
  const idTitulo = useId();

  useEffect(() => {
    if (!abierto) {
      return;
    }

    const manejarTecla = (evento: KeyboardEvent) => {
      if (evento.key === 'Escape' && !bloquearCierre) {
        onCerrar();
      }
    };

    document.addEventListener('keydown', manejarTecla);

    return () => document.removeEventListener('keydown', manejarTecla);
  }, [abierto, bloquearCierre, onCerrar]);

  if (!abierto) {
    return null;
  }

  return (
    <div
      className={estilos.modalFondo}
      onMouseDown={(evento) => {
        if (!bloquearCierre && evento.target === evento.currentTarget) {
          onCerrar();
        }
      }}
    >
      <div
        aria-labelledby={idTitulo}
        aria-modal="true"
        className={estilos.modal}
        role="dialog"
      >
        <header className={estilos.modalCabecera}>
          <div>
            <h2 className={estilos.modalTitulo} id={idTitulo}>
              {titulo}
            </h2>
            {descripcion ? <p>{descripcion}</p> : null}
          </div>
          <button
            aria-label="Cerrar"
            className={estilos.modalCerrar}
            disabled={bloquearCierre}
            onClick={onCerrar}
            type="button"
          >
            ×
          </button>
        </header>

        <div className={estilos.modalCuerpo}>{children}</div>

        {pie ? <footer className={estilos.modalPie}>{pie}</footer> : null}
      </div>
    </div>
  );
}
