import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '../auth/AuthContext';
import { borrarSesion, guardarSesion } from '../auth/almacenSesion';
import type { Rol } from '../auth/permisos';
import { solicitarUsuarioActual } from '../auth/servicioAuth';
import { AppLayout } from './AppLayout';

vi.mock('../auth/servicioAuth', () => ({
  iniciarSesionApi: vi.fn(),
  cerrarSesionApi: vi.fn().mockResolvedValue(undefined),
  solicitarUsuarioActual: vi.fn(),
}));

const contadorDeudoresMock = vi.hoisted(() => vi.fn());

vi.mock('../../modules/cobros/useContadorDeudores', () => ({
  useContadorDeudores: contadorDeudoresMock,
}));

function renderizar(rol: Rol, ruta = '/padron') {
  guardarSesion({ token: 'token-test', rol, usuario: 'Prueba' });

  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={[ruta]}>
        <Routes>
          <Route path="/login" element={<h1>Login</h1>} />
          <Route element={<AppLayout />}>
            <Route path="/panel" element={<h1>Panel</h1>} />
            <Route path="/padron" element={<h1>Dueños y mascotas</h1>} />
            <Route path="/guarderia/calendario" element={<h1>Calendario</h1>} />
            <Route path="/guarderia/nueva" element={<h1>Nueva reserva</h1>} />
            <Route path="/turnos" element={<h1>Turnos</h1>} />
            <Route path="/historia-clinica" element={<h1>Historia clínica</h1>} />
            <Route path="/cobros" element={<h1>Cobros</h1>} />
            <Route path="/cobros/deudores" element={<h1>Deudores</h1>} />
            <Route path="/migracion" element={<h1>Migración</h1>} />
            <Route
              path="/identidad/crear-cuenta"
              element={<h1>Crear cuenta</h1>}
            />
          </Route>
        </Routes>
      </MemoryRouter>
    </AuthProvider>,
  );
}

function navegaciones() {
  return {
    lateral: screen.getByRole('navigation', { name: 'Navegación lateral' }),
    inferior: screen.getByRole('navigation', { name: 'Navegación inferior' }),
  };
}

/** Enlaces del menú lateral, sin la marca ni el pie. */
function enlacesLateral(): string[] {
  const { lateral } = navegaciones();

  return within(lateral)
    .getAllByRole('link')
    .filter((enlace) => enlace.closest('li') !== null)
    .map((enlace) => enlace.textContent?.trim() ?? '');
}

beforeEach(() => {
  borrarSesion();
  vi.mocked(solicitarUsuarioActual).mockRejectedValue(
    new Error('La verificación de sesión no aplica en este test.'),
  );
  contadorDeudoresMock.mockReset();
  contadorDeudoresMock.mockReturnValue(null);
});

describe('AppLayout', () => {
  it('sin sesión redirige a login', async () => {
    render(
      <AuthProvider>
        <MemoryRouter initialEntries={['/padron']}>
          <Routes>
            <Route path="/login" element={<h1>Login</h1>} />
            <Route element={<AppLayout />}>
              <Route path="/padron" element={<h1>Dueños y mascotas</h1>} />
            </Route>
          </Routes>
        </MemoryRouter>
      </AuthProvider>,
    );

    expect(await screen.findByRole('heading', { name: 'Login' })).toBeInTheDocument();
  });

  it('DUENIO ve sus 8 secciones en el orden pedido', () => {
    renderizar('DUENIO');

    expect(enlacesLateral()).toEqual([
      'Panel',
      'Dueños y mascotas',
      'Calendario',
      'Nueva reserva',
      'Historia clínica',
      'Cobros',
      'Deudores',
      'Crear cuenta',
    ]);
  });

  it('DUENIO ve la cantidad de deudores en el menú', async () => {
    const usuario = userEvent.setup();
    contadorDeudoresMock.mockReturnValue(7);
    renderizar('DUENIO');
    const { lateral, inferior } = navegaciones();

    expect(
      within(lateral).getByRole('link', { name: 'Deudores: 7' }),
    ).toBeInTheDocument();

    await usuario.click(within(inferior).getByRole('button', { name: 'Más' }));

    expect(
      within(inferior).getByRole('link', { name: 'Deudores: 7' }),
    ).toBeInTheDocument();
  });

  it('no muestra número cuando no hay deudores', () => {
    contadorDeudoresMock.mockReturnValue(0);
    renderizar('DUENIO');
    const { lateral } = navegaciones();

    expect(within(lateral).getByRole('link', { name: 'Deudores' })).toHaveTextContent(
      /^Deudores$/,
    );
  });

  it.each([
    ['DUENIO', true],
    ['PERSONAL', false],
    ['VETERINARIO', false],
  ] as const)(
    '%s consulta el contador solo si Deudores está en su menú',
    (rol, activo) => {
      renderizar(rol);

      expect(contadorDeudoresMock).toHaveBeenCalledWith(activo, '/padron');
    },
  );

  it.each(['PERSONAL', 'VETERINARIO'] as const)('%s no ve Panel', (rol) => {
    renderizar(rol);
    const { lateral, inferior } = navegaciones();

    expect(within(lateral).queryByRole('link', { name: 'Panel' })).not.toBeInTheDocument();
    expect(within(inferior).queryByRole('link', { name: 'Panel' })).not.toBeInTheDocument();
  });

  it('PERSONAL ve Dueños y mascotas, Calendario, Nueva reserva, Cobros y Turnos', () => {
    renderizar('PERSONAL');

    expect(enlacesLateral()).toEqual([
      'Dueños y mascotas',
      'Calendario',
      'Nueva reserva',
      'Cobros',
      'Turnos',
    ]);
  });

  it('PERSONAL no ve Historia clínica, Deudores ni Migración', () => {
    renderizar('PERSONAL');
    const { lateral, inferior } = navegaciones();

    for (const nombre of ['Historia clínica', 'Deudores', 'Migración']) {
      expect(within(lateral).queryByRole('link', { name: nombre })).not.toBeInTheDocument();
      expect(within(inferior).queryByRole('link', { name: nombre })).not.toBeInTheDocument();
    }
  });

  it('VETERINARIO ve Dueños y mascotas, Calendario, Turnos e Historia clínica', () => {
    renderizar('VETERINARIO');

    expect(enlacesLateral()).toEqual([
      'Dueños y mascotas',
      'Calendario',
      'Turnos',
      'Historia clínica',
    ]);
  });

  it('VETERINARIO no ve Cobros, Deudores ni Nueva reserva', () => {
    renderizar('VETERINARIO');
    const { lateral, inferior } = navegaciones();

    for (const nombre of ['Cobros', 'Deudores', 'Nueva reserva']) {
      expect(within(lateral).queryByRole('link', { name: nombre })).not.toBeInTheDocument();
      expect(within(inferior).queryByRole('link', { name: nombre })).not.toBeInTheDocument();
    }
  });

  it('DUENIO encuentra Historia clínica, Cobros, Deudores y Crear cuenta en Más', async () => {
    const usuario = userEvent.setup();
    renderizar('DUENIO');
    const { inferior } = navegaciones();

    await usuario.click(within(inferior).getByRole('button', { name: 'Más' }));

    expect(within(inferior).getByRole('link', { name: 'Historia clínica' })).toBeInTheDocument();
    expect(within(inferior).getByRole('link', { name: 'Cobros' })).toBeInTheDocument();
    expect(within(inferior).getByRole('link', { name: 'Deudores' })).toBeInTheDocument();
    expect(within(inferior).getByRole('link', { name: 'Crear cuenta' })).toBeInTheDocument();
  });

  it.each(['PERSONAL', 'VETERINARIO'] as const)('%s no ve Crear cuenta', (rol) => {
    renderizar(rol);
    const { lateral, inferior } = navegaciones();

    expect(within(lateral).queryByRole('link', { name: 'Crear cuenta' })).not.toBeInTheDocument();
    expect(within(inferior).queryByRole('link', { name: 'Crear cuenta' })).not.toBeInTheDocument();
  });

  it('en Deudores solo se destaca Deudores, no Cobros', async () => {
    const usuario = userEvent.setup();
    renderizar('DUENIO', '/cobros/deudores');
    const { lateral, inferior } = navegaciones();

    expect(within(lateral).getByRole('link', { name: 'Deudores' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    expect(within(lateral).getByRole('link', { name: 'Cobros' })).not.toHaveAttribute(
      'aria-current',
    );

    await usuario.click(within(inferior).getByRole('button', { name: 'Más' }));

    expect(within(inferior).getByRole('link', { name: 'Deudores' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    expect(within(inferior).getByRole('link', { name: 'Cobros' })).not.toHaveAttribute(
      'aria-current',
    );
  });

  it('el encabezado muestra la sección actual y la fecha de hoy', () => {
    renderizar('DUENIO', '/padron');

    const encabezado = screen.getByRole('banner');
    const migaja = within(encabezado).getByRole('navigation', { name: 'Ubicación' });
    const fecha = encabezado.querySelector('time');

    expect(
      within(migaja).getByRole('link', { name: 'Huellitas, ir al inicio' }),
    ).toBeInTheDocument();
    expect(within(migaja).getByText('Dueños y mascotas')).toHaveAttribute(
      'aria-current',
      'page',
    );
    expect(within(migaja).queryByText('Inicio')).not.toBeInTheDocument();
    expect(within(encabezado).queryByRole('button', { name: 'Salir' })).not.toBeInTheDocument();
    expect(fecha).not.toBeNull();
    expect(fecha?.textContent?.trim()).not.toBe('');
    expect(fecha?.getAttribute('datetime')).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it.each([
    ['/cobros/deudores', 'Deudores'],
    ['/guarderia/calendario', 'Calendario'],
    ['/guarderia/nueva', 'Nueva reserva'],
    ['/historia-clinica', 'Historia clínica'],
    ['/identidad/crear-cuenta', 'Crear cuenta'],
    ['/turnos', 'Turnos'],
    ['/migracion', 'Migración'],
  ] as const)('el encabezado corresponde a la sección de %s', (ruta, etiqueta) => {
    renderizar('DUENIO', ruta);

    const migaja = within(screen.getByRole('banner')).getByRole('navigation', {
      name: 'Ubicación',
    });

    expect(within(migaja).getByText(etiqueta)).toHaveAttribute('aria-current', 'page');
  });

  it.each([
    ['/turnos', 'Turnos'],
    ['/migracion', 'Migración'],
  ] as const)(
    'DUENIO puede entrar a %s por URL aunque no esté en el menú',
    (ruta, nombre) => {
      renderizar('DUENIO', ruta);
      const { lateral } = navegaciones();

      expect(within(lateral).queryByRole('link', { name: nombre })).not.toBeInTheDocument();
      expect(screen.getByRole('heading', { name: nombre })).toBeInTheDocument();
    },
  );
});
