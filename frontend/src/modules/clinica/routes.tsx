import type { RouteObject } from 'react-router-dom';

import { RequireRole } from '../../core/auth/RequireRole';
import { PantallaProvisoria } from '../../core/components/PantallaProvisoria';

export const clinicaRoutes: RouteObject[] = [
  {
    path: '/turnos',
    element: (
      <RequireRole seccion="turnos">
        <PantallaProvisoria
          seccion="turnos"
          titulo="Turnos"
          descripcion="Agenda veterinaria y turnos del personal (mañana, tarde y noche)."
        />
      </RequireRole>
    ),
  },
  {
    path: '/historia-clinica',
    element: (
      <RequireRole seccion="historia-clinica">
        <PantallaProvisoria
          seccion="historia-clinica"
          titulo="Historia clínica"
          descripcion="Consultas, vacunas, cirugías y tratamientos de cada mascota."
        />
      </RequireRole>
    ),
  },
];
