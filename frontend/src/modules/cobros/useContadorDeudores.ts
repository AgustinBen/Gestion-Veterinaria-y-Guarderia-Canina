import { useEffect, useState } from 'react';

import { listarDeudores } from './api';

/** El backend acepta como máximo 100 deudores por consulta. */
const LIMITE_CONTADOR = 100;

/**
 * Cantidad de clientes con deuda para el contador del menú (RN-21/RN-23).
 *
 * - `activo` evita consultar cuando el rol no tiene "Deudores" en el menú.
 * - `refresco` vuelve a consultar al navegar para que el número no quede viejo.
 * - Si la API falla no se muestra número: el menú nunca se bloquea por esto.
 */
export function useContadorDeudores(
  activo: boolean,
  refresco: string,
): number | null {
  const [cantidad, setCantidad] = useState<number | null>(null);

  useEffect(() => {
    if (!activo) {
      return;
    }

    const control = new AbortController();

    listarDeudores({
      orden: 'monto',
      limite: LIMITE_CONTADOR,
      signal: control.signal,
    })
      .then((filas) => {
        if (!control.signal.aborted) {
          setCantidad(filas.length);
        }
      })
      .catch(() => {
        if (!control.signal.aborted) {
          setCantidad(null);
        }
      });

    return () => control.abort();
  }, [activo, refresco]);

  return activo ? cantidad : null;
}
