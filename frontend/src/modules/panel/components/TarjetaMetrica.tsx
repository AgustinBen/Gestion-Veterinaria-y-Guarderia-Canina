import type { ReactNode } from 'react';

import { formatearDinero } from '../../../core/formatos/dinero';
import estilos from '../panel.module.css';

type Props = {
  titulo: string;
  valor: number | null;
  motivo?: string | null;
  pie?: ReactNode;
  destacada?: boolean;
};

/**
 * Tarjeta de una métrica del panel. Si la API devuelve `null`, muestra "—" y
 * el motivo en texto: el significado no depende del color.
 */
export function TarjetaMetrica({
  titulo,
  valor,
  motivo,
  pie,
  destacada = false,
}: Props) {
  return (
    <section
      aria-label={titulo}
      className={[estilos.tarjeta, destacada ? estilos.tarjetaDestacada : '']
        .filter(Boolean)
        .join(' ')}
    >
      <h2 className={estilos.tarjetaTitulo}>{titulo}</h2>
      <p className={estilos.tarjetaValor}>
        {valor === null ? (
          <span aria-label={`${titulo}: sin dato`}>—</span>
        ) : (
          formatearDinero(valor)
        )}
      </p>
      {valor === null && motivo ? (
        <p className={estilos.tarjetaMotivo}>{motivo}</p>
      ) : null}
      {pie ? <div className={estilos.tarjetaPie}>{pie}</div> : null}
    </section>
  );
}
