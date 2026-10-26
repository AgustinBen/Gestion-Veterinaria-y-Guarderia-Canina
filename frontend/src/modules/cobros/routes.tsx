import type { RouteObject } from 'react-router-dom';

import { RequireRole } from '../../core/auth/RequireRole';
import { PantallaProvisoria } from '../../core/components/PantallaProvisoria';

export const cobrosRoutes: RouteObject[] = [
  {
    path: '/cobros',
    element: (
      <RequireRole seccion="cobros">
        <PantallaProvisoria
          seccion="cobros"
          titulo="Cobros"
          descripcion="Servicios, pagos, medios de pago y saldos calculados automáticamente."
        />
      </RequireRole>
    ),
  },
  {
    path: '/cobros/deudores',
    element: (
      <RequireRole seccion="deudores">
        <PantallaProvisoria
          seccion="deudores"
          titulo="Deudores"
          descripcion="Clientes con saldo pendiente. La deuda muestra una alerta visible y nunca bloquea."
        />
      </RequireRole>
    ),
  },
];
