import type { RouteObject } from 'react-router-dom';

import { RequireRole } from '../../core/auth/RequireRole';
import { AltaPaciente } from './pages/AltaPaciente';
import { AltaPersona } from './pages/AltaPersona';
import { Buscador } from './pages/Buscador';
import { FichaPaciente } from './pages/FichaPaciente';
import { FichaPersona } from './pages/FichaPersona';
import { Titulares } from './pages/Titulares';

export const padronRoutes: RouteObject[] = [
  {
    path: '/padron',
    element: (
      <RequireRole seccion="padron">
        <Buscador />
      </RequireRole>
    ),
  },
  {
    path: '/padron/alta-persona',
    element: (
      <RequireRole seccion="padron" nivel="escritura">
        <AltaPersona />
      </RequireRole>
    ),
  },
  {
    path: '/padron/persona/:id',
    element: (
      <RequireRole seccion="padron">
        <FichaPersona />
      </RequireRole>
    ),
  },
  {
    path: '/padron/persona/:id/editar',
    element: (
      <RequireRole seccion="padron" nivel="escritura">
        <AltaPersona />
      </RequireRole>
    ),
  },
  {
    path: '/padron/alta-paciente',
    element: (
      <RequireRole seccion="padron" nivel="escritura">
        <AltaPaciente />
      </RequireRole>
    ),
  },
  {
    path: '/padron/paciente/:id',
    element: (
      <RequireRole seccion="padron">
        <FichaPaciente />
      </RequireRole>
    ),
  },
  {
    path: '/padron/paciente/:id/editar',
    element: (
      <RequireRole seccion="padron" nivel="escritura">
        <AltaPaciente />
      </RequireRole>
    ),
  },
  {
    path: '/padron/paciente/:id/titulares',
    element: (
      <RequireRole seccion="padron">
        <Titulares />
      </RequireRole>
    ),
  },
];
