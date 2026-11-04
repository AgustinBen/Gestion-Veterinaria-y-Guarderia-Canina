import type { ReactNode } from 'react';

import { EtiquetaCampo } from './EtiquetaCampo';
import estilos from './ui.module.css';

type Props = {
  id: string;
  etiqueta: string;
  obligatorio?: boolean;
  ayuda?: ReactNode;
  error?: string;
  children: ReactNode;
};

export function Campo({
  id,
  etiqueta,
  obligatorio = false,
  ayuda,
  error,
  children,
}: Props) {
  return (
    <div className={estilos.campo}>
      <EtiquetaCampo htmlFor={id} obligatorio={obligatorio}>
        {etiqueta}
      </EtiquetaCampo>
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
