import { Navigate, type RouteObject } from 'react-router-dom';

import { RequireRole } from '../../core/auth/RequireRole';
import { PantallaProvisoria } from '../../core/components/PantallaProvisoria';

export const guarderiaRoutes: RouteObject[] = [
  {
    path: '/guarderia',
    element: <Navigate to="/guarderia/calendario" replace />,
  },
  {
    path: '/guarderia/calendario',
    element: (
      <RequireRole seccion="calendario">
        <PantallaProvisoria
          seccion="calendario"
          titulo="Calendario"
          descripcion="Cupo de guardería por fecha y franja, con plazas disponibles y de emergencia."
        />
      </RequireRole>
    ),
  },
  {
    path: '/guarderia/nueva',
    element: (
      <RequireRole seccion="nueva-reserva">
        <PantallaProvisoria
          seccion="nueva-reserva"
          titulo="Nueva reserva"
          descripcion="Alta de reserva de guardería con seña obligatoria y control de cupo."
        />
      </RequireRole>
    ),
  },
];
