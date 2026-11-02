import { useEffect, useState } from 'react';

import { obtenerTitulares } from '../../padron/api';
import type { TitularVigente } from '../../padron/tipos';

type Props = {
  pacienteId: number;
};

type Resultado = {
  pacienteId: number;
  titulares: TitularVigente[] | null;
};

/**
 * Dueño de la mascota (titular principal vigente). Distingue a dos mascotas
 * con el mismo nombre. Si falla la consulta no bloquea la pantalla.
 */
export function DuenioMascota({ pacienteId }: Props) {
  const [resultado, setResultado] = useState<Resultado | null>(null);

  useEffect(() => {
    const controlador = new AbortController();

    obtenerTitulares(pacienteId, { signal: controlador.signal })
      .then((titulares) => {
        if (!controlador.signal.aborted) {
          setResultado({ pacienteId, titulares });
        }
      })
      .catch(() => {
        if (!controlador.signal.aborted) {
          setResultado({ pacienteId, titulares: null });
        }
      });

    return () => controlador.abort();
  }, [pacienteId]);

  // Mientras no haya respuesta para esta mascota se muestra "cargando".
  if (resultado === null || resultado.pacienteId !== pacienteId) {
    return <span>Dueño: …</span>;
  }

  const titulares = resultado.titulares ?? [];
  const principal =
    titulares.find((titular) => titular.principal) ?? titulares[0];

  if (!principal) {
    return <span>Dueño: sin datos</span>;
  }

  const otros = titulares.length - 1;

  return (
    <span>
      Dueño:{' '}
      <strong>
        {principal.nombre} {principal.apellido}
      </strong>
      {otros > 0 ? ` (+${otros})` : ''}
    </span>
  );
}
