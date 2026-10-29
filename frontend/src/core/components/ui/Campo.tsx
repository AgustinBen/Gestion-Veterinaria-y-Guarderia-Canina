import type { ReactNode } from 'react';

import estilos from './ui.module.css';

type Props = {
  id: string;
  etiqueta: string;
  ayuda?: ReactNode;
  error?: string;
  children: ReactNode;
};

export function Campo({ id, etiqueta, ayuda, error, children }: Props) {
  return (
    <div className={estilos.campo}>
      <label htmlFor={id}>{etiqueta}</label>
      {children}
      {error ? (
        <p className={estilos.errorCampo} id={`${id}-error`}>
          {error}
        </p>
      ) : ayuda ? (
        <p className={estilos.ayuda} id={`${id}-ayuda`}>
          {ayuda}
        </p>
      ) : null}
    </div>
  );
}
