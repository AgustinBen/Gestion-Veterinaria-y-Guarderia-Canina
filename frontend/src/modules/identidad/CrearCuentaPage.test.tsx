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
  await usuario.type(screen.getByLabelText('Usuario'), username);
  await usuario.type(screen.getByLabelText('Contraseña'), password);
  await usuario.type(screen.getByLabelText('Nombre'), 'Ana');
  await usuario.type(screen.getByLabelText('Apellido'), 'Paz');
  await usuario.type(screen.getByLabelText('DNI'), '30111222');
  await usuario.type(screen.getByLabelText('Teléfono'), '1155550101');
}

const EMPLEADO_ESPERADO = {
  nombre: 'Ana',
  apellido: 'Paz',
  dni: '30111222',
  telefono: '1155550101',
};

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
    crearUsuarioMock.mockResolvedValueOnce({
      username: 'recepcion',
      rol,
      empleado_id: 7,
    });

    renderizar('DUENIO');
    await ingresarDatos(usuario);
    await usuario.click(screen.getByRole('radio', { name: new RegExp(etiquetaRol) }));
    if (rol === 'VETERINARIO') {
      await usuario.type(screen.getByLabelText('Especialidad (opcional)'), 'Cirugía');
    } else {
      expect(screen.queryByLabelText('Especialidad (opcional)')).not.toBeInTheDocument();
    }
    await usuario.click(screen.getByRole('button', { name: 'Crear cuenta' }));

    expect(await screen.findByRole('status')).toHaveTextContent(
      `La cuenta de recepcion con rol ${etiquetaRol} fue creada.`,
    );
    expect(crearUsuarioMock).toHaveBeenCalledWith({
      username: 'recepcion',
      password: 'clave-segura',
      rol,
      empleado: {
        ...EMPLEADO_ESPERADO,
        ...(rol === 'VETERINARIO' ? { especialidad: 'Cirugía' } : {}),
      },
    });
    expect(screen.getByLabelText('Contraseña')).toHaveValue('');
    expect(screen.getByRole('status')).not.toHaveTextContent('clave-segura');
    expect(window.localStorage.getItem('huellitas.sesion')).not.toContain('clave-segura');
  });

  it('descarta letras y símbolos en el teléfono', async () => {
    const usuario = userEvent.setup();
    crearUsuarioMock.mockResolvedValueOnce({
      username: 'recepcion',
      rol: 'PERSONAL',
      empleado_id: 7,
    });

    renderizar('DUENIO');
    await ingresarDatos(usuario);
    const telefono = screen.getByLabelText('Teléfono');

    await usuario.clear(telefono);
    await usuario.type(telefono, '11 2345-66u8abc');
    expect(telefono).toHaveValue('112345668');

    await usuario.click(screen.getByRole('button', { name: 'Crear cuenta' }));

    expect(crearUsuarioMock).toHaveBeenCalledWith(
      expect.objectContaining({
        empleado: expect.objectContaining({ telefono: '112345668' }),
      }),
    );
  });

  it('pide confirmar un posible duplicado y reenvía con la confirmación', async () => {
    const usuario = userEvent.setup();
    crearUsuarioMock
      .mockRejectedValueOnce(
        new ApiError('Hay posibles duplicados', {
          tipo: 'http',
          estado: 409,
          detalle: {
            codigo: 'POSIBLE_DUPLICADO',
            coincidencias: [
              {
                persona: { nombre: 'Ana', apellido: 'Paz' },
                motivo: 'Teléfono repetido',
              },
            ],
          },
        }),
      )
      .mockResolvedValueOnce({
        username: 'recepcion',
        rol: 'PERSONAL',
        empleado_id: 9,
      });

    renderizar('DUENIO');
    await ingresarDatos(usuario);
    await usuario.click(screen.getByRole('button', { name: 'Crear cuenta' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Teléfono repetido');
    expect(screen.getByRole('button', { name: 'Crear cuenta' })).toBeDisabled();

    await usuario.click(screen.getByLabelText(/Confirmo que es otra persona/));
    await usuario.click(screen.getByRole('button', { name: 'Crear cuenta' }));

    expect(await screen.findByRole('status')).toHaveTextContent('La cuenta de recepcion');
    expect(crearUsuarioMock).toHaveBeenLastCalledWith(
      expect.objectContaining({
        empleado: { ...EMPLEADO_ESPERADO, confirmar_duplicado: true },
      }),
    );
  });

  it('informa un DNI ya registrado sin permitir confirmarlo', async () => {
    const usuario = userEvent.setup();
    crearUsuarioMock.mockRejectedValueOnce(
      new ApiError('El DNI ya está registrado', {
        tipo: 'http',
        estado: 409,
        detalle: { codigo: 'DNI_DUPLICADO', persona: { nombre: 'Ana' } },
      }),
    );

    renderizar('DUENIO');
    await ingresarDatos(usuario);
    await usuario.click(screen.getByRole('button', { name: 'Crear cuenta' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Ya existe una persona con ese DNI.',
    );
    expect(screen.queryByLabelText(/Confirmo que es otra persona/)).not.toBeInTheDocument();
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

    expect(screen.getAllByRole('button', { name: 'Volver' })).toHaveLength(1);
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
    expect(screen.getByLabelText('Usuario')).toHaveValue('recepcion');
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
      'Los datos ingresados no son válidos. Revisá los datos de acceso y los del empleado.',
    );
    expect(screen.getByLabelText('Usuario')).toHaveValue('recepcion');
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
      .mockResolvedValueOnce({
        username: 'recepcion',
        rol: 'PERSONAL',
        empleado_id: null,
      });

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
    let completarCreacion: (resultado: {
      username: string;
      rol: 'PERSONAL';
      empleado_id: null;
    }) => void = () => {
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

    completarCreacion({
      username: 'recepcion',
      rol: 'PERSONAL',
      empleado_id: null,
    });
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Crear cuenta' })).toBeEnabled();
    });
  });
});
