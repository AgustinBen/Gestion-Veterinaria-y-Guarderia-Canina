import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AuthContext } from '../../../core/auth/contexto';
import type { Rol } from '../../../core/auth/permisos';
import { listarEmpleados, obtenerPaciente } from '../../padron/api';
import { marcarTurnoAusente, obtenerTurno } from '../api';
import { DetalleTurno } from '../pages/DetalleTurno';
import type { Turno } from '../tipos';

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>();

  return {
    ...actual,
    marcarTurnoAusente: vi.fn(),
    obtenerTurno: vi.fn(),
  };
});

vi.mock('../../padron/api', () => ({
  listarEmpleados: vi.fn(),
  obtenerPaciente: vi.fn(),
}));

const TURNO: Turno = {
  id: 15,
  paciente_id: 4,
  tipo: 'CONSULTA',
  veterinario_empleado_id: 7,
  inicio: '2026-11-02T09:00:00',
  fin: '2026-11-02T09:30:00',
  estado: 'PROGRAMADO',
  motivo: null,
  atencion_id: null,
  externo_actual_id: null,
  cargo_id: null,
  created_by: 1,
  created_at: '2026-10-30T10:00:00',
};

function renderizar(rol: Rol) {
  return render(
    <AuthContext.Provider
      value={{
        sesion: { token: 'token', rol, usuario: 'prueba' },
        iniciarSesion: vi.fn(),
        cerrarSesion: vi.fn(),
      }}
    >
      <MemoryRouter initialEntries={['/turnos/15']}>
        <Routes>
          <Route element={<DetalleTurno />} path="/turnos/:turnoId" />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
}

describe('DetalleTurno · marcar ausente', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(obtenerTurno).mockResolvedValue(TURNO);
    vi.mocked(listarEmpleados).mockResolvedValue([]);
    vi.mocked(obtenerPaciente).mockResolvedValue({
      id: 4,
      nombre: 'Luna',
    } as never);
  });

  it('pide confirmación y no marca la ausencia hasta confirmar', async () => {
    vi.mocked(marcarTurnoAusente).mockResolvedValue({
      ...TURNO,
      estado: 'AUSENTE',
    });
    renderizar('DUENIO');

    fireEvent.click(
      await screen.findByRole('button', { name: 'Marcar ausente' }),
    );

    expect(await screen.findByRole('dialog')).toHaveTextContent(
      '¿Confirmás que la mascota no se presentó al turno?',
    );
    expect(marcarTurnoAusente).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole('button', { name: 'Confirmar ausencia' }));

    await waitFor(() => expect(marcarTurnoAusente).toHaveBeenCalledWith(15));
    expect(
      await screen.findByText('El turno quedó marcado como ausente.'),
    ).toBeInTheDocument();
  });

  it('al volver desde la confirmación no marca la ausencia', async () => {
    renderizar('PERSONAL');

    fireEvent.click(
      await screen.findByRole('button', { name: 'Marcar ausente' }),
    );
    const dialogo = await screen.findByRole('dialog');
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Volver' }));

    await waitFor(() =>
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument(),
    );
    expect(marcarTurnoAusente).not.toHaveBeenCalled();
  });
});
