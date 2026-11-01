import { render, screen } from '@testing-library/react';
import { MemoryRouter, useRoutes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { AuthContext, type ValorAuth } from '../../../core/auth/contexto';
import type { Rol } from '../../../core/auth/permisos';
import { guarderiaRoutes } from '../routes';

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>();

  return {
    ...actual,
    listarCalendario: vi.fn().mockResolvedValue([]),
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
  it('PERSONAL puede abrir calendario y crear reservas', async () => {
    renderizar('PERSONAL', '/guarderia/calendario');

    expect(
      await screen.findByRole('heading', { name: 'Calendario de agenda' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Nueva reserva' })).toHaveAttribute(
      'href',
      '/guarderia/nueva',
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
