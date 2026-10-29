import { render, screen } from '@testing-library/react';
import { MemoryRouter, useRoutes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '../../../core/auth/AuthContext';
import { borrarSesion, guardarSesion } from '../../../core/auth/almacenSesion';
import type { Rol } from '../../../core/auth/permisos';
import { listarDeudores } from '../api';
import { cobrosRoutes } from '../routes';

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>();

  return {
    ...actual,
    listarDeudores: vi.fn(),
  };
});

vi.mock('../../../core/auth/servicioAuth', () => ({
  iniciarSesionApi: vi.fn(),
  cerrarSesionApi: vi.fn().mockResolvedValue(undefined),
  solicitarUsuarioActual: vi
    .fn()
    .mockRejectedValue(new Error('La verificación de sesión no aplica en este test.')),
}));

function Rutas() {
  return useRoutes([
    ...cobrosRoutes,
    { path: '/sin-acceso', element: <h1>Sin acceso</h1> },
    { path: '/login', element: <h1>Login</h1> },
  ]);
}

function renderizar(ruta: string, rol?: Rol) {
  borrarSesion();

  if (rol) {
    guardarSesion({ token: 'token-test', rol, usuario: 'Prueba' });
  }

  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={[ruta]}>
        <Rutas />
      </MemoryRouter>
    </AuthProvider>,
  );
}

beforeEach(() => {
  vi.mocked(listarDeudores).mockReset();
  vi.mocked(listarDeudores).mockResolvedValue([]);
});

describe('rutas de cobros', () => {
  it('VETERINARIO no puede entrar a Cobros y vuelve a sin acceso', () => {
    renderizar('/cobros', 'VETERINARIO');

    expect(screen.getByRole('heading', { name: 'Sin acceso' })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Cobros' })).not.toBeInTheDocument();
  });

  it('VETERINARIO tampoco puede entrar a Deudores', () => {
    renderizar('/cobros/deudores', 'VETERINARIO');

    expect(screen.getByRole('heading', { name: 'Sin acceso' })).toBeInTheDocument();
    expect(listarDeudores).not.toHaveBeenCalled();
  });

  it('PERSONAL puede entrar a Cobros pero no ve el acceso a Deudores', () => {
    renderizar('/cobros', 'PERSONAL');

    expect(screen.getByRole('heading', { name: 'Cobros' })).toBeInTheDocument();
    expect(screen.getByLabelText('Buscar cliente')).toBeInTheDocument();
    expect(
      screen.queryByRole('link', { name: 'Ver deudores' }),
    ).not.toBeInTheDocument();
  });

  it('PERSONAL no puede entrar a Deudores por URL', () => {
    renderizar('/cobros/deudores', 'PERSONAL');

    expect(screen.getByRole('heading', { name: 'Sin acceso' })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Deudores' })).not.toBeInTheDocument();
    expect(listarDeudores).not.toHaveBeenCalled();
  });

  it('DUENIO ve el acceso a Deudores desde Cobros', () => {
    renderizar('/cobros', 'DUENIO');

    expect(screen.getByRole('heading', { name: 'Cobros' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Ver deudores' })).toHaveAttribute(
      'href',
      '/cobros/deudores',
    );
  });

  it('DUENIO puede entrar a Deudores', async () => {
    renderizar('/cobros/deudores', 'DUENIO');

    expect(screen.getByRole('heading', { name: 'Deudores' })).toBeInTheDocument();
    expect(
      await screen.findByText('No hay clientes con deuda pendiente.'),
    ).toBeInTheDocument();
  });

  it('sin sesión redirige al login', () => {
    renderizar('/cobros');

    expect(screen.getByRole('heading', { name: 'Login' })).toBeInTheDocument();
  });
});
