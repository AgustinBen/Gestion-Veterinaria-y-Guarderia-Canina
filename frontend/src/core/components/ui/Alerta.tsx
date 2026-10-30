import type { AriaRole, ReactNode } from 'react';

import estilos from './ui.module.css';

export type TonoAlerta = 'info' | 'aviso' | 'error' | 'exito';

type Props = {
  tono?: TonoAlerta;
  role?: AriaRole;
  children: ReactNode;
  acciones?: ReactNode;
};

const CLASE_TONO: Record<TonoAlerta, string | undefined> = {
  info: undefined,
  aviso: estilos.alertaAviso,
  error: estilos.alertaError,
  exito: estilos.alertaExito,
};

export function Alerta({ tono = 'info', role, children, acciones }: Props) {
  return (
    <div
      className={[estilos.alerta, CLASE_TONO[tono]].filter(Boolean).join(' ')}
      role={role}
    >
      <div>{children}</div>
      {acciones ? <div className={estilos.alertaAcciones}>{acciones}</div> : null}
    </div>
  );
}
