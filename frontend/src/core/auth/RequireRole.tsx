import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';

import { useAuth } from './contexto';
import { puedeAcceder, type NivelAcceso, type SeccionId } from './permisos';

type Props = {
  seccion: SeccionId;
  nivel?: NivelAcceso;
  children: ReactNode;
};

export function RequireRole({ seccion, nivel = 'lectura', children }: Props) {
  const { sesion } = useAuth();
  const ubicacion = useLocation();

  if (!sesion) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ desde: `${ubicacion.pathname}${ubicacion.search}` }}
      />
    );
  }

  if (!puedeAcceder(sesion.rol, seccion, nivel)) {
    return <Navigate to="/sin-acceso" replace />;
  }

  return <>{children}</>;
}
