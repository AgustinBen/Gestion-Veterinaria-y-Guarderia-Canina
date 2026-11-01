import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AuthContext, type ValorAuth } from '../../../core/auth/contexto';
import {
  generarIdempotencyKey,
  obtenerReserva,
  registrarSena,
} from '../api';
import { listarMediosPago } from '../../cobros/api';
import { obtenerPaciente } from '../../padron/api';
import { DetalleReserva } from '../pages/DetalleReserva';
import type { PacienteDetalle } from '../../padron/tipos';
import type { Reserva } from '../tipos';
import type { Rol } from '../../../core/auth/permisos';

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>();

  return {
    ...actual,
    generarIdempotencyKey: vi.fn(() => 'clave-sena-detalle'),
    obtenerReserva: vi.fn(),
    registrarSena: vi.fn(),
  };
});

vi.mock('../../cobros/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../cobros/api')>();

  return { ...actual, listarMediosPago: vi.fn() };
});

vi.mock('../../padron/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../padron/api')>();

  return { ...actual, obtenerPaciente: vi.fn() };
});

const RESERVA_PENDIENTE: Reserva = {
  id: 71,
  tutor_persona_id: 8,
  desde_fecha: '2026-12-14',
  desde_franja: 'DIA',
  hasta_fecha: '2026-12-14',
  hasta_franja: 'NOCHE',
  estado: 'PENDIENTE_SENA',
  cargo_id: 51,
  total_centavos: 123456,
  sena_centavos: 0,
  pacientes: [
    {
      paciente_id: 21,
      cuidados_extras: true,
      tipo_cuidado: 'Administrar medicación',
    },
  ],
  created_at: '2026-11-01T10:00:00',
};

const RESERVA_CONFIRMADA: Reserva = {
  ...RESERVA_PENDIENTE,
  estado: 'CONFIRMADA',
  sena_centavos: 5000,
};

const MASCOTA: PacienteDetalle = {
  id: 21,
  nombre: 'Luna',
  especie_id: 1,
  especie_nombre: 'Perro',
  raza_id: null,
  raza_nombre: null,
  tamanio_id: null,
  tamanio_nombre: null,
  peso_kg: null,
  fecha_nacimiento_aprox: null,
  castrado: null,
  activo: true,
  edad_anios: null,
  edad_meses: null,
};

function valorAuth(rol: Rol): ValorAuth {
  return {
    sesion: { token: 'token-prueba', rol, usuario: 'prueba' },
    iniciarSesion: vi.fn(),
    cerrarSesion: vi.fn(),
  };
}

function renderizar(rol: Rol) {
  return render(
    <AuthContext.Provider value={valorAuth(rol)}>
      <MemoryRouter initialEntries={['/guarderia/reservas/71']}>
        <Routes>
          <Route
            element={<DetalleReserva />}
            path="/guarderia/reservas/:reservaId"
          />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
}

beforeEach(() => {
  vi.mocked(generarIdempotencyKey).mockReturnValue('clave-sena-detalle');
  vi.mocked(obtenerReserva).mockReset();
  vi.mocked(registrarSena).mockReset();
  vi.mocked(listarMediosPago).mockReset();
  vi.mocked(obtenerPaciente).mockReset();
  vi.mocked(obtenerReserva).mockResolvedValue(RESERVA_PENDIENTE);
  vi.mocked(obtenerPaciente).mockResolvedValue(MASCOTA);
  vi.mocked(listarMediosPago).mockResolvedValue([
    { id: 1, codigo: 'EFECTIVO', nombre: 'Efectivo', activo: true },
  ]);
  vi.mocked(registrarSena).mockResolvedValue(RESERVA_CONFIRMADA);
});

describe('DetalleReserva', () => {
  it('muestra el estado, el tramo, el total, la seña y las mascotas', async () => {
    renderizar('VETERINARIO');

    expect(await screen.findByText('Pendiente de seña')).toBeInTheDocument();
    expect(screen.getByText('14/12 (día) – 14/12 (noche)')).toBeInTheDocument();
    expect(screen.getByText('$1.234,56')).toBeInTheDocument();
    expect(screen.getByText('$0,00 · Pendiente')).toBeInTheDocument();
    expect(screen.getByText('Luna · Perro')).toBeInTheDocument();
    expect(screen.getByText('Cuidados extras: Sí')).toBeInTheDocument();
    expect(screen.getByText('Tipo de cuidado: Administrar medicación')).toBeInTheDocument();
  });

  it('permite a PERSONAL registrar la seña y actualiza el detalle', async () => {
    renderizar('PERSONAL');

    await screen.findByRole('heading', { name: 'Reserva #71' });
    fireEvent.click(screen.getByRole('button', { name: 'Registrar seña' }));
    fireEvent.change(await screen.findByLabelText('Monto de la seña'), {
      target: { value: '50' },
    });
    fireEvent.change(screen.getByLabelText('Medio de pago'), {
      target: { value: 'EFECTIVO' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar seña' }));

    expect(await screen.findByText('Confirmada')).toBeInTheDocument();
    expect(screen.getByText('$50,00')).toBeInTheDocument();
    expect(registrarSena).toHaveBeenCalledWith(
      71,
      { monto_centavos: 5000, medio: 'EFECTIVO' },
      { idempotencyKey: 'clave-sena-detalle' },
    );
  });

  it('mantiene VETERINARIO en solo lectura y no consulta medios de cobro', async () => {
    renderizar('VETERINARIO');

    await screen.findByRole('heading', { name: 'Reserva #71' });

    expect(screen.queryByRole('button', { name: 'Registrar seña' })).not.toBeInTheDocument();
    expect(listarMediosPago).not.toHaveBeenCalled();
    expect(registrarSena).not.toHaveBeenCalled();
  });

  it('permite reintentar si falla la carga del detalle', async () => {
    vi.mocked(obtenerReserva)
      .mockRejectedValueOnce(new Error('Sin conexión'))
      .mockResolvedValueOnce(RESERVA_PENDIENTE);
    renderizar('PERSONAL');

    expect(await screen.findByRole('alert')).toHaveTextContent('Sin conexión');
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }));

    expect(await screen.findByRole('heading', { name: 'Reserva #71' }))
      .toBeInTheDocument();
    await waitFor(() => expect(obtenerReserva).toHaveBeenCalledTimes(2));
  });
});
