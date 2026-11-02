import type { RouteObject } from 'react-router-dom';

import { RequireRole } from '../../core/auth/RequireRole';
import { DetalleTurno } from './pages/DetalleTurno';
import { HistoriaClinica } from './pages/HistoriaClinica';
import { NuevoTurnoPage } from './pages/NuevoTurnoPage';
import { Pacientes } from './pages/Pacientes';
import { Turnos } from './pages/Turnos';

export const clinicaRoutes: RouteObject[] = [
  {
    path: '/turnos',
    element: (
      <RequireRole seccion="turnos">
        <Turnos />
      </RequireRole>
    ),
  },
  {
    path: '/turnos/nueva',
    element: (
      <RequireRole nivel="escritura" seccion="nueva-reserva">
        <NuevoTurnoPage />
      </RequireRole>
    ),
  },
  {
    path: '/turnos/:turnoId',
    element: (
      <RequireRole seccion="turnos">
        <DetalleTurno />
      </RequireRole>
    ),
  },
  {
    path: '/historia-clinica',
    element: (
      <RequireRole seccion="historia-clinica">
        <Pacientes />
      </RequireRole>
    ),
  },
  {
    path: '/historia-clinica/:pacienteId',
    element: (
      <RequireRole seccion="historia-clinica">
        <HistoriaClinica />
      </RequireRole>
    ),
  },
];
