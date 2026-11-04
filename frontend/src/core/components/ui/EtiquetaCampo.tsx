import type { ReactNode } from 'react';

import estilos from './ui.module.css';

type MarcaProps = {
  className?: string;
};

/**
 * Marca visual de campo obligatorio. Es solo decorativa: el dato accesible
 * sigue siendo el texto de la etiqueta.
 */
export function MarcaObligatorio({ className }: MarcaProps) {
  return (
    <span
      aria-hidden="true"
      className={[estilos.marcaObligatorio, className].filter(Boolean).join(' ')}
    >
      *
    </span>
  );
}

type Props = {
  htmlFor: string;
  /** Texto de la etiqueta. Si se omite, se usa `children` como texto. */
  etiqueta?: ReactNode;
  children?: ReactNode;
  obligatorio?: boolean;
  className?: string;
};

/**
 * Etiqueta compartida por todos los formularios. Centraliza el asterisco rojo
 * de los campos obligatorios para que el estilo sea uniforme.
 *
 * Cuando la etiqueta envuelve al control (por ejemplo un input dentro del
 * label), se pasa el texto en `etiqueta` y el control en `children` para que
 * el asterisco quede junto al texto y no después del control.
 *
 * El asterisco se dibuja con `::after` sobre el texto para que no forme parte
 * del nombre accesible de la etiqueta.
 */
export function EtiquetaCampo({
  htmlFor,
  etiqueta,
  children,
  obligatorio = false,
  className,
}: Props) {
  const texto = etiqueta ?? children;

  return (
    <label className={className} htmlFor={htmlFor}>
      {obligatorio ? (
        <span className={estilos.obligatorio}>{texto}</span>
      ) : (
        texto
      )}
      {etiqueta !== undefined ? children : null}
    </label>
  );
}
