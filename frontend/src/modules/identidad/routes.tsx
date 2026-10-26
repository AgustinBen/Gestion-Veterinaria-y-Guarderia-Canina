import type { RouteObject } from 'react-router-dom';

import { LoginPage } from './LoginPage';

export const identidadRoutes: RouteObject[] = [
  {
    path: '/login',
    element: <LoginPage />,
  },
];
