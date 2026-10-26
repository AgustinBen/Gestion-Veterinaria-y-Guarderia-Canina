import type { RouteObject } from 'react-router-dom';

import { RequireRole } from '../../core/auth/RequireRole';
import { PantallaProvisoria } from '../../core/components/PantallaProvisoria';

export const panelRoutes: RouteObject[] = [
  {
    path: '/panel',
    element: (
      <RequireRole seccion="panel">
        <PantallaProvisoria
          seccion="panel"
          titulo="Panel"
          descripcion="Resumen de finanzas, métricas y gastos a externos del negocio."
        />
      </RequireRole>
    ),
  },
];
