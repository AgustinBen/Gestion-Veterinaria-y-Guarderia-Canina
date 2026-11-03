import type { RouteObject } from 'react-router-dom';

import { RequireRole } from '../../core/auth/RequireRole';
import { Categorias } from './pages/Categorias';
import { DetalleCliente } from './pages/DetalleCliente';
import { Egresos } from './pages/Egresos';
import { GastosExternos } from './pages/GastosExternos';
import { Tablero } from './pages/Tablero';

/**
 * Rutas del panel financiero. Solo el Dueño tiene el recurso `finanzas`
 * (RN-40); Personal y Veterinario terminan en "sin acceso".
 */
export const panelRoutes: RouteObject[] = [
  {
    path: '/panel',
    element: (
      <RequireRole nivel="escritura" seccion="panel">
        <Tablero />
      </RequireRole>
    ),
  },
  {
    path: '/panel/egresos',
    element: (
      <RequireRole nivel="escritura" seccion="panel">
        <Egresos />
      </RequireRole>
    ),
  },
  {
    path: '/panel/gastos-externos',
    element: (
      <RequireRole nivel="escritura" seccion="panel">
        <GastosExternos />
      </RequireRole>
    ),
  },
  {
    path: '/panel/categorias',
    element: (
      <RequireRole nivel="escritura" seccion="panel">
        <Categorias />
      </RequireRole>
    ),
  },
  {
    path: '/panel/cliente/:personaId',
    element: (
      <RequireRole nivel="escritura" seccion="panel">
        <DetalleCliente />
      </RequireRole>
    ),
  },
];
