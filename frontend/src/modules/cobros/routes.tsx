import type { RouteObject } from 'react-router-dom';

import { RequireRole } from '../../core/auth/RequireRole';
import { Cobrar } from './pages/Cobrar';
import { CuentaCliente } from './pages/CuentaCliente';
import { Deudores } from './pages/Deudores';

export const cobrosRoutes: RouteObject[] = [
  {
    path: '/cobros',
    element: (
      <RequireRole nivel="escritura" seccion="cobros">
        <Cobrar />
      </RequireRole>
    ),
  },
  {
    path: '/cobros/cliente/:personaId',
    element: (
      <RequireRole nivel="escritura" seccion="cobros">
        <CuentaCliente />
      </RequireRole>
    ),
  },
  {
    path: '/cobros/deudores',
    element: (
      <RequireRole seccion="deudores">
        <Deudores />
      </RequireRole>
    ),
  },
];
