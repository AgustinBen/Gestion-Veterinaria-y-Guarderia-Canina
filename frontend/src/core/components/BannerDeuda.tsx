import { Link } from 'react-router-dom';

import { formatearDinero } from '../formatos/dinero';
import estilos from './BannerDeuda.module.css';

export type PropsBannerDeuda = {
  debe: boolean;
  saldoTotalCentavos: number;
  deudaMasAntigua?: string | null;
  personaId: number;
};

/** "2026-03-05" → "05/03" sin pasar por zonas horarias. */
function formatearFechaCorta(fecha: string | null | undefined): string | null {
  if (!fecha) {
    return null;
  }

  const coincidencia = /^(\d{4})-(\d{2})-(\d{2})/.exec(fecha);

  return coincidencia ? `${coincidencia[3]}/${coincidencia[2]}` : null;
}

/**
 * Alerta de deuda reutilizable por cobros, guardería y el buscador.
 *
 * RN-23: avisa pero nunca bloquea. Este componente no renderiza controles que
 * impidan continuar; el flujo que lo use decide si pide una confirmación.
 */
export function BannerDeuda({
  debe,
  saldoTotalCentavos,
  deudaMasAntigua,
  personaId,
}: PropsBannerDeuda) {
  if (!debe || saldoTotalCentavos <= 0) {
    return null;
  }

  const desde = formatearFechaCorta(deudaMasAntigua);

  return (
    <aside aria-label="Deuda pendiente" className={estilos.banner}>
      <p className={estilos.texto}>
        Debe <strong>{formatearDinero(saldoTotalCentavos)}</strong>
        {desde ? ` desde ${desde}` : ''}
      </p>
      <Link className={estilos.enlace} to={`/cobros/cliente/${personaId}`}>
        Ver cuenta
      </Link>
    </aside>
  );
}
