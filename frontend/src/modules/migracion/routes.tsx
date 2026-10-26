import type { RouteObject } from 'react-router-dom';

import { RequireRole } from '../../core/auth/RequireRole';
import { PantallaProvisoria } from '../../core/components/PantallaProvisoria';

export const migracionRoutes: RouteObject[] = [
  {
    path: '/migracion',
    element: (
      <RequireRole seccion="migracion">
        <PantallaProvisoria
          seccion="migracion"
          titulo="Migración"
          descripcion="Importación del Excel histórico, reporte de altas y revisión de casos dudosos."
        />
      </RequireRole>
    ),
  },
];
