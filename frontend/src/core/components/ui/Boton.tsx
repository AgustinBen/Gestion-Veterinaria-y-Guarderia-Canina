import type { ButtonHTMLAttributes, ReactNode } from 'react';

import estilos from './ui.module.css';

export type VarianteBoton = 'primario' | 'secundario' | 'peligro' | 'texto';

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variante?: VarianteBoton;
  bloque?: boolean;
  cargando?: boolean;
  children: ReactNode;
};

const CLASE_VARIANTE: Record<VarianteBoton, string | undefined> = {
  primario: undefined,
  secundario: estilos.botonSecundario,
  peligro: estilos.botonPeligro,
  texto: estilos.botonTexto,
};

export function Boton({
  variante = 'primario',
  bloque = false,
  cargando = false,
  children,
  className,
  disabled,
  type = 'button',
  ...resto
}: Props) {
  const clases = [
    estilos.boton,
    CLASE_VARIANTE[variante],
    bloque ? estilos.botonBloque : undefined,
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <button
      {...resto}
      aria-busy={cargando || undefined}
      className={clases}
      disabled={disabled === true || cargando}
      type={type}
    >
      {cargando ? 'Procesando…' : children}
    </button>
  );
}
