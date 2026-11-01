import { Navigate, type RouteObject } from 'react-router-dom';

import { RequireRole } from '../../core/auth/RequireRole';
import { Calendario } from './pages/Calendario';
import { DetalleReserva } from './pages/DetalleReserva';
import { NuevaReserva } from './pages/NuevaReserva';

export const guarderiaRoutes: RouteObject[] = [
  {
    path: '/guarderia',
    element: <Navigate to="/guarderia/calendario" replace />,
  },
  {
    path: '/guarderia/calendario',
    element: (
      <RequireRole seccion="calendario">
        <Calendario />
      </RequireRole>
    ),
  },
  {
    path: '/guarderia/reservar',
    element: (
      <RequireRole nivel="escritura" seccion="nueva-reserva">
        <NuevaReserva />
      </RequireRole>
    ),
  },
  {
    path: '/guarderia/nueva',
    element: <Navigate to="/guarderia/reservar" replace />,
  },
  {
    path: '/guarderia/reservas/:reservaId',
    element: (
      <RequireRole seccion="calendario">
        <DetalleReserva />
      </RequireRole>
    ),
  },
];
