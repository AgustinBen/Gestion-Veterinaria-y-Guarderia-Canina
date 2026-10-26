import type { RouteObject } from 'react-router-dom';

import { RequireRole } from '../../core/auth/RequireRole';
import { PantallaProvisoria } from '../../core/components/PantallaProvisoria';

export const padronRoutes: RouteObject[] = [
  {
    path: '/padron',
    element: (
      <RequireRole seccion="padron">
        <PantallaProvisoria
          seccion="padron"
          titulo="Dueños y mascotas"
          descripcion="Alta y búsqueda de dueños, mascotas, contactos y características de cada animal."
        />
      </RequireRole>
    ),
  },
];
