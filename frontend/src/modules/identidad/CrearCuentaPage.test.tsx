import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '../../core/api/client';
import { AuthProvider } from '../../core/auth/AuthContext';
import { borrarSesion, guardarSesion } from '../../core/auth/almacenSesion';
import { RequireRole } from '../../core/auth/RequireRole';
import { solicitarUsuarioActual } from '../../core/auth/servicioAuth';
import { CrearCuentaPage } from './CrearCuentaPage';
import { crearUsuario } from './servicioUsuarios';

vi.mock('../../core/auth/servicioAuth', () => ({
  iniciarSesionApi: vi.fn(),
  cerrarSesionApi: vi.fn().mockResolvedValue(undefined),
  solicitarUsuarioActual: vi.fn(),
}));

vi.mock('./servicioUsuarios', () => ({
  crearUsuario: vi.fn(),
}));

const crearUsuarioMock = vi.mocked(crearUsuario);

function renderizar(rol: 'DUENIO' | 'PERSONAL' | 'VETERINARIO') {
  guardarSesion({ token: 'token-test', rol, usuario: 'Prueba' });

  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={['/identidad/crear-cuenta']}>
        <Routes>
          <Route path="/" element={<h1>Inicio</h1>} />
          <Route path="/login" element={<h1>Iniciar sesión</h1>} />
          <Route path="/sin-acceso" element={<h1>Sin acceso</h1>} />
          <Route
            path="/identidad/crear-cuenta"
            element={
              <RequireRole seccion="crear-cuenta">
                <CrearCuentaPage />
              </RequireRole>
            }
          />
        </Routes>
      </MemoryRouter>
    </AuthProvider>,
  );
}

async function ingresarDatos(
  usuario: ReturnType<typeof userEvent.setup>,
  username = 'recepcion',
  password = 'clave-segura',
) {
  await usuario.type(screen.getByLabelText('Nombre de usuario'), username);
  await usuario.type(screen.getByLabelText('Contraseña'), password);
}

beforeEach(() => {
  borrarSesion();
  crearUsuarioMock.mockReset();
  vi.mocked(solicitarUsuarioActual).mockRejectedValue(
    new Error('La verificación de sesión no aplica en este test.'),
  );
});

describe('CrearCuentaPage', () => {
  it.each([
    ['PERSONAL', 'Personal'],
    ['VETERINARIO', 'Veterinario'],
  ] as const)('DUENIO puede crear una cuenta %s', async (rol, etiquetaRol) => {
    const usuario = userEvent.setup();
    crearUsuarioMock.mockResolvedValueOnce({ username: 'recepcion', rol });

    renderizar('DUENIO');
    await ingresarDatos(usuario);
    await usuario.selectOptions(screen.getByLabelText('Rol'), rol);
    await usuario.click(screen.getByRole('button', { name: 'Crear cuenta' }));

    expect(await screen.findByRole('status')).toHaveTextContent(
      `La cuenta de recepcion con rol ${etiquetaRol} fue creada.`,
    );
    expect(crearUsuarioMock).toHaveBeenCalledWith({
      username: 'recepcion',
      password: 'clave-segura',
      rol,
    });
    expect(screen.getByLabelText('Contraseña')).toHaveValue('');
    expect(screen.getByRole('status')).not.toHaveTextContent('clave-segura');
    expect(window.localStorage.getItem('huellitas.sesion')).not.toContain('clave-segura');
  });

  it.each(['PERSONAL', 'VETERINARIO'] as const)(
    '%s no puede entrar a Crear cuenta por URL',
    async (rol) => {
      renderizar(rol);

      expect(await screen.findByRole('heading', { name: 'Sin acceso' })).toBeInTheDocument();
      expect(screen.queryByLabelText('Contraseña')).not.toBeInTheDocument();
    },
  );

  it('ofrece volver y desde una URL directa regresa al inicio', async () => {
    const usuario = userEvent.setup();

    renderizar('DUENIO');

    await usuario.click(screen.getByRole('button', { name: 'Volver' }));

    expect(await screen.findByRole('heading', { name: 'Inicio' })).toBeInTheDocument();
  });

  it('muestra un error entendible para un username duplicado y conserva los datos', async () => {
    const usuario = userEvent.setup();
    crearUsuarioMock.mockRejectedValueOnce(
      new ApiError('El username ya está registrado', { tipo: 'http', estado: 409 }),
    );

    renderizar('DUENIO');
    await ingresarDatos(usuario);
    await usuario.click(screen.getByRole('button', { name: 'Crear cuenta' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Ese nombre de usuario ya está registrado. Probá con otro.',
    );
    expect(screen.getByLabelText('Nombre de usuario')).toHaveValue('recepcion');
    expect(screen.getByLabelText('Contraseña')).toHaveValue('clave-segura');
    expect(screen.getByRole('button', { name: 'Crear cuenta' })).toBeEnabled();
  });

  it('explica el error 422 del backend sin perder los datos', async () => {
    const usuario = userEvent.setup();
    crearUsuarioMock.mockRejectedValueOnce(
      new ApiError('Error 422 al comunicarse con el servidor.', {
        tipo: 'http',
        estado: 422,
      }),
    );

    renderizar('DUENIO');
    await ingresarDatos(usuario);
    await usuario.click(screen.getByRole('button', { name: 'Crear cuenta' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Los datos ingresados no son válidos. Revisá el nombre de usuario y la contraseña.',
    );
    expect(screen.getByLabelText('Nombre de usuario')).toHaveValue('recepcion');
    expect(screen.getByLabelText('Contraseña')).toHaveValue('clave-segura');
    expect(screen.getByRole('button', { name: 'Crear cuenta' })).toBeEnabled();
  });

  it('permite reintentar después de un error de red', async () => {
    const usuario = userEvent.setup();
    crearUsuarioMock
      .mockRejectedValueOnce(
        new ApiError('No pudimos conectar con el servidor.', {
          tipo: 'red',
          reintentable: true,
        }),
      )
      .mockResolvedValueOnce({ username: 'recepcion', rol: 'PERSONAL' });

    renderizar('DUENIO');
    await ingresarDatos(usuario);
    await usuario.click(screen.getByRole('button', { name: 'Crear cuenta' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No pudimos conectar con el servidor.',
    );
    expect(screen.getByRole('button', { name: 'Crear cuenta' })).toBeEnabled();

    await usuario.click(screen.getByRole('button', { name: 'Crear cuenta' }));

    expect(await screen.findByRole('status')).toHaveTextContent('La cuenta de recepcion');
    expect(crearUsuarioMock).toHaveBeenCalledTimes(2);
  });

  it('bloquea un segundo envío mientras el primero sigue pendiente', async () => {
    const usuario = userEvent.setup();
    let completarCreacion: (resultado: { username: string; rol: 'PERSONAL' }) => void = () => {
      throw new Error('La solicitud no se inició.');
    };
    crearUsuarioMock.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          completarCreacion = resolve;
        }),
    );

    renderizar('DUENIO');
    await ingresarDatos(usuario);

    const formulario = screen.getByRole('button', { name: 'Crear cuenta' }).closest('form');
    if (!formulario) {
      throw new Error('No se encontró el formulario de creación.');
    }

    fireEvent.submit(formulario);
    fireEvent.submit(formulario);

    expect(crearUsuarioMock).toHaveBeenCalledTimes(1);
    expect(screen.getByRole('button', { name: 'Creando cuenta…' })).toBeDisabled();

    completarCreacion({ username: 'recepcion', rol: 'PERSONAL' });
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Crear cuenta' })).toBeEnabled();
    });
  });
});
