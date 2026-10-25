import { BrowserRouter, Navigate, useRoutes, type RouteObject } from 'react-router-dom';

import { useAuth } from './auth/contexto';
import { rutaInicial } from './auth/permisos';
import { SinAccesoPage } from './auth/SinAccesoPage';
import { AppLayout } from './layout/AppLayout';
import { clinicaRoutes } from '../modules/clinica/routes';
import { cobrosRoutes } from '../modules/cobros/routes';
import { guarderiaRoutes } from '../modules/guarderia/routes';
import { identidadRoutes } from '../modules/identidad/routes';
import { migracionRoutes } from '../modules/migracion/routes';
import { padronRoutes } from '../modules/padron/routes';
import { panelRoutes } from '../modules/panel/routes';

function InicioRedirect() {
  const { sesion } = useAuth();

  return <Navigate to={sesion ? rutaInicial(sesion.rol) : '/login'} replace />;
}

const rutas: RouteObject[] = [
  ...identidadRoutes,
  {
    path: '/sin-acceso',
    element: <SinAccesoPage />,
  },
  {
    element: <AppLayout />,
    children: [
      { index: true, element: <InicioRedirect /> },
      ...panelRoutes,
      ...padronRoutes,
      ...cobrosRoutes,
      ...guarderiaRoutes,
      ...clinicaRoutes,
      ...migracionRoutes,
    ],
  },
  {
    path: '*',
    element: <Navigate to="/" replace />,
  },
];

function RutasApp() {
  return useRoutes(rutas);
}

export function AppRouter() {
  return (
    <BrowserRouter>
      <RutasApp />
    </BrowserRouter>
  );
}
