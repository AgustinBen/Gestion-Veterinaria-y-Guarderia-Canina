import { render, screen } from '@testing-library/react';
import { MemoryRouter, useRoutes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { AuthContext, type ValorAuth } from '../../../core/auth/contexto';
import type { Rol } from '../../../core/auth/permisos';
import { fechaLocal } from '../fechas';
import { guarderiaRoutes } from '../routes';

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>();

  return {
    ...actual,
    listarCalendario: vi.fn().mockResolvedValue([]),
    obtenerConfiguracionCupo: vi.fn().mockResolvedValue({
      cupo_maximo: 4,
      cupo_minimo: 2,
      cupo_maximo_permitido: 4,
      sobreocupaciones: [],
    }),
  };
});

vi.mock('../../cobros/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../cobros/api')>();

  return {
    ...actual,
    listarMediosPago: vi.fn().mockResolvedValue([]),
  };
});

function Rutas() {
  return useRoutes([
    ...guarderiaRoutes,
    { path: '/sin-acceso', element: <p>Sin acceso</p> },
  ]);
}

function valorAuth(rol: Rol): ValorAuth {
  return {
    sesion: { token: 'token-prueba', rol, usuario: 'prueba' },
    iniciarSesion: vi.fn(),
    cerrarSesion: vi.fn(),
  };
}

function renderizar(rol: Rol, ruta: string) {
  return render(
    <AuthContext.Provider value={valorAuth(rol)}>
      <MemoryRouter initialEntries={[ruta]}>
        <Rutas />
      </MemoryRouter>
    </AuthContext.Provider>,
  );
}

describe('rutas de guardería y permisos', () => {
  it('solo DUENIO puede abrir la configuración del cupo', async () => {
    renderizar('DUENIO', '/guarderia/configuracion');

    expect(
      await screen.findByRole('heading', { name: 'Configuración del cupo' }),
    ).toBeInTheDocument();
  });

  it.each(['PERSONAL', 'VETERINARIO'] as const)(
    '%s no puede abrir la configuración del cupo por URL',
    async (rol) => {
      renderizar(rol, '/guarderia/configuracion');

      expect(await screen.findByText('Sin acceso')).toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Guardar cupo' })).not.toBeInTheDocument();
    },
  );

  it('PERSONAL puede abrir calendario y crear reservas', async () => {
    renderizar('PERSONAL', '/guarderia/calendario');

    expect(
      await screen.findByRole('heading', { name: 'Calendario de agenda' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Nueva reserva' })).toHaveAttribute(
      'href',
      `/guarderia/reservar?fecha=${fechaLocal(new Date())}`,
    );
  });

  it('VETERINARIO ve el calendario pero no el botón de nueva reserva', async () => {
    renderizar('VETERINARIO', '/guarderia/calendario');

    expect(
      await screen.findByRole('heading', { name: 'Calendario de agenda' }),
    ).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Nueva reserva' })).not.toBeInTheDocument();
  });

  it('VETERINARIO no puede abrir la ruta de alta aunque ingrese la URL', async () => {
    renderizar('VETERINARIO', '/guarderia/reservar');

    expect(await screen.findByText('Sin acceso')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Reservar' })).not.toBeInTheDocument();
  });
});
