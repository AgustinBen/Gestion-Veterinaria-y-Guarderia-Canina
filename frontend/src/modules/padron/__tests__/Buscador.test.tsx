import { act, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '../../../core/api/client';
import { AuthProvider } from '../../../core/auth/AuthContext';
import { guardarSesion } from '../../../core/auth/almacenSesion';
import type { Rol } from '../../../core/auth/permisos';
import {
  buscarPersonas,
  listarPacientes,
  obtenerPersona,
} from '../api';
import { Buscador } from '../pages/Buscador';
import type { PacienteResumen, PersonaDetalle, PersonaResumen } from '../tipos';

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>();

  return {
    ...actual,
    buscarPersonas: vi.fn(),
    listarPacientes: vi.fn(),
    obtenerPersona: vi.fn(),
  };
});

const ANA: PersonaResumen = {
  id: 3,
  nombre: 'Ana',
  apellido: 'Paz',
  dni: '30111222',
  dni_pendiente: false,
  telefonos: ['1144556677'],
};

const FIRULAIS: PacienteResumen = {
  id: 8,
  nombre: 'Firulais',
  especie_id: 1,
  especie_nombre: 'Perro',
  raza_id: null,
  raza_nombre: null,
  activo: true,
};

const ANA_DETALLE: PersonaDetalle = {
  ...ANA,
  domicilio: null,
  creado_en: '2026-10-01T10:00:00',
  duplicado_confirmado: false,
  mascotas: [
    {
      id: 8,
      nombre: 'Firulais',
      especie_id: 1,
      especie_nombre: 'Perro',
      raza_id: null,
      raza_nombre: null,
      activo: true,
    },
  ],
};

function renderizar(rol: Rol = 'PERSONAL') {
  guardarSesion({ token: 'token-test', rol, usuario: 'Prueba' });

  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={['/padron']}>
        <Routes>
          <Route path="/padron" element={<Buscador />} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>,
  );
}

async function avanzarBusqueda(ms = 250) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

beforeEach(() => {
  vi.useFakeTimers();
  vi.mocked(buscarPersonas).mockReset();
  vi.mocked(listarPacientes).mockReset();
  vi.mocked(obtenerPersona).mockReset();

  vi.mocked(listarPacientes).mockResolvedValue([]);
});

afterEach(() => {
  vi.useRealTimers();
});

describe('Buscador de padrón', () => {
  it('muestra las mascotas registradas como tarjetas al entrar', async () => {
    vi.useRealTimers();
    vi.mocked(listarPacientes).mockResolvedValue([FIRULAIS]);
    renderizar();

    expect(
      screen.getByRole('heading', { name: 'Mascotas registradas' }),
    ).toBeInTheDocument();
    expect(await screen.findByText('Firulais')).toBeInTheDocument();
    expect(screen.getByText('Perro')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Firulais/ })).toHaveAttribute(
      'href',
      '/padron/paciente/8',
    );
  });

  it('muestra el error del listado y permite reintentarlo', async () => {
    vi.useRealTimers();
    vi.mocked(listarPacientes).mockRejectedValueOnce(
      new ApiError('No pudimos conectar con el servidor.', {
        tipo: 'red',
        reintentable: true,
      }),
    );
    renderizar();

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No pudimos conectar con el servidor.',
    );

    vi.mocked(listarPacientes).mockResolvedValueOnce([FIRULAIS]);
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }));

    expect(await screen.findByText('Firulais')).toBeInTheDocument();
    expect(listarPacientes).toHaveBeenCalledTimes(2);
  });

  it('espera el debounce antes de consultar la API', async () => {
    vi.mocked(buscarPersonas).mockResolvedValue([]);
    renderizar();

    fireEvent.change(screen.getByLabelText('Buscar'), { target: { value: 'Ana' } });

    await avanzarBusqueda(249);
    expect(buscarPersonas).not.toHaveBeenCalled();

    await avanzarBusqueda(1);
    expect(buscarPersonas).toHaveBeenCalledTimes(1);
    expect(buscarPersonas).toHaveBeenCalledWith(
      'Ana',
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
  });

  it('muestra primero la mascota encontrada y el titular como dato secundario', async () => {
    vi.mocked(buscarPersonas).mockResolvedValue([ANA]);
    vi.mocked(obtenerPersona).mockResolvedValue(ANA_DETALLE);
    renderizar();

    fireEvent.change(screen.getByLabelText('Buscar'), { target: { value: 'Paz' } });
    await avanzarBusqueda();

    expect(screen.getByText('Firulais')).toBeInTheDocument();
    expect(screen.getByText('Persona vinculada: Paz, Ana')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Firulais/ })).toHaveAttribute(
      'href',
      '/padron/paciente/8',
    );
    expect(obtenerPersona).toHaveBeenCalledWith(3, expect.anything());
  });

  it('avisa cuando no hay resultados', async () => {
    vi.mocked(buscarPersonas).mockResolvedValue([]);
    renderizar();

    fireEvent.change(screen.getByLabelText('Buscar'), { target: { value: 'Nadie' } });
    await avanzarBusqueda();

    expect(
      screen.getByText('No encontramos dueños ni mascotas con ese dato.'),
    ).toBeInTheDocument();
  });

  it('muestra el error de red y permite reintentar', async () => {
    vi.mocked(buscarPersonas).mockRejectedValueOnce(
      new ApiError('No pudimos conectar con el servidor.', { tipo: 'red', reintentable: true }),
    );
    renderizar();

    fireEvent.change(screen.getByLabelText('Buscar'), { target: { value: 'Ana' } });
    await avanzarBusqueda();

    expect(screen.getByRole('alert')).toHaveTextContent(
      'No pudimos conectar con el servidor.',
    );

    vi.mocked(buscarPersonas).mockResolvedValueOnce([ANA]);
    vi.mocked(obtenerPersona).mockResolvedValueOnce(ANA_DETALLE);

    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }));
    await avanzarBusqueda();

    expect(screen.getByText('Firulais')).toBeInTheDocument();
    expect(buscarPersonas).toHaveBeenCalledTimes(2);
  });

  it('PERSONAL ve el alta de dueño y VETERINARIO no', () => {
    vi.mocked(buscarPersonas).mockResolvedValue([]);

    const { unmount } = renderizar('PERSONAL');
    expect(screen.getByRole('link', { name: 'Nuevo dueño' })).toBeInTheDocument();
    unmount();

    renderizar('VETERINARIO');
    expect(screen.queryByRole('link', { name: 'Nuevo dueño' })).not.toBeInTheDocument();
  });
});
