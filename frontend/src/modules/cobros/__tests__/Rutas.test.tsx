import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, useRoutes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '../../../core/auth/AuthContext';
import { borrarSesion, guardarSesion } from '../../../core/auth/almacenSesion';
import type { Rol } from '../../../core/auth/permisos';
import { buscarPersonas, listarDeudores } from '../api';
import { cobrosRoutes } from '../routes';

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>();

  return {
    ...actual,
    buscarPersonas: vi.fn(),
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
  vi.mocked(buscarPersonas).mockReset();
  vi.mocked(buscarPersonas).mockResolvedValue([]);
  vi.mocked(listarDeudores).mockReset();
  vi.mocked(listarDeudores).mockResolvedValue([]);
});

function persona(id: number) {
  return {
    id,
    nombre: `Nombre ${id}`,
    apellido: `Apellido ${id}`,
    dni: `${id}`,
    dni_pendiente: false,
    telefonos: [],
  };
}

describe('rutas de cobros', () => {
  it('carga y pagina el listado inicial de clientes', async () => {
    vi.mocked(buscarPersonas).mockImplementation((_texto, opciones) =>
      Promise.resolve(
        opciones?.offset === 0
          ? Array.from({ length: 6 }, (_, indice) => persona(indice + 1))
          : [persona(6)],
      ),
    );
    const usuario = userEvent.setup();
    renderizar('/cobros', 'PERSONAL');

    expect(
      await screen.findByRole('link', { name: /Apellido 1, Nombre 1/ }),
    ).toBeInTheDocument();
    await waitFor(() =>
      expect(buscarPersonas).toHaveBeenCalledWith(
        '',
        expect.objectContaining({ limite: 6, offset: 0 }),
      ),
    );
    expect(screen.getByText('1–5')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Clientes' })).toBeInTheDocument();
    expect(screen.queryByText('Cuentas')).not.toBeInTheDocument();
    expect(
      screen.queryByText(/Buscá un dueño por nombre, DNI o teléfono/),
    ).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /Apellido 6, Nombre 6/ })).not.toBeInTheDocument();

    await usuario.click(screen.getByRole('button', { name: 'Siguiente' }));

    expect(
      await screen.findByRole('link', { name: /Apellido 6, Nombre 6/ }),
    ).toBeInTheDocument();
    expect(buscarPersonas).toHaveBeenLastCalledWith(
      '',
      expect.objectContaining({ limite: 6, offset: 5 }),
    );
    expect(screen.getByText('Página 2')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Siguiente' })).toBeDisabled();
  });

  it('reinicia la página cuando cambia la búsqueda', async () => {
    vi.mocked(buscarPersonas).mockImplementation((texto, opciones) =>
      Promise.resolve(
        texto
          ? [persona(30)]
          : opciones?.offset === 0
            ? Array.from({ length: 6 }, (_, indice) => persona(indice + 1))
            : [persona(6)],
      ),
    );
    const usuario = userEvent.setup();
    renderizar('/cobros', 'PERSONAL');
    await screen.findByRole('link', { name: /Apellido 1, Nombre 1/ });
    await usuario.click(screen.getByRole('button', { name: 'Siguiente' }));
    await screen.findByRole('link', { name: /Apellido 6, Nombre 6/ });

    fireEvent.change(screen.getByRole('searchbox', { name: 'Buscar cliente' }), {
      target: { value: 'Nombre 30' },
    });

    expect(
      await screen.findByRole('link', { name: /Apellido 30, Nombre 30/ }),
    ).toBeInTheDocument();
    expect(buscarPersonas).toHaveBeenLastCalledWith(
      'Nombre 30',
      expect.objectContaining({ limite: 6, offset: 0 }),
    );
    expect(screen.getByText('Página 1')).toBeInTheDocument();
  });

  it('muestra errores de carga y permite reintentar', async () => {
    vi.mocked(buscarPersonas)
      .mockRejectedValueOnce(new Error('No se pudo cargar clientes.'))
      .mockResolvedValueOnce([persona(1)]);
    const usuario = userEvent.setup();
    renderizar('/cobros', 'PERSONAL');

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No se pudo cargar clientes.',
    );
    await usuario.click(screen.getByRole('button', { name: 'Reintentar' }));

    expect(
      await screen.findByRole('link', { name: /Apellido 1, Nombre 1/ }),
    ).toBeInTheDocument();
  });

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
    expect(screen.getByText('Buscar cliente', { selector: 'label' })).toHaveClass('sr-only');
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
