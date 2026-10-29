import type { RouteObject } from 'react-router-dom';

import { RequireRole } from '../../core/auth/RequireRole';
import { CrearCuentaPage } from './CrearCuentaPage';
import { LoginPage } from './LoginPage';

export const identidadRoutes: RouteObject[] = [
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/identidad/crear-cuenta',
    element: (
      <RequireRole seccion="crear-cuenta">
        <CrearCuentaPage />
      </RequireRole>
    ),
  },
];
