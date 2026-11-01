import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '../../core/auth/AuthContext';
import { borrarSesion, leerSesion } from '../../core/auth/almacenSesion';
import { iniciarSesionApi, solicitarUsuarioActual } from '../../core/auth/servicioAuth';
import { LoginPage } from './LoginPage';

vi.mock('../../core/auth/servicioAuth', () => ({
  iniciarSesionApi: vi.fn(),
  cerrarSesionApi: vi.fn().mockResolvedValue(undefined),
  solicitarUsuarioActual: vi.fn(),
}));

const iniciarSesionApiMock = vi.mocked(iniciarSesionApi);

function renderizarLogin() {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={['/login']}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/panel" element={<h1>Panel</h1>} />
          <Route path="/sin-acceso" element={<h1>Sin acceso</h1>} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>,
  );
}

async function completarFormulario(usuario: string, password: string) {
  const usuarioEvento = userEvent.setup();

  await usuarioEvento.type(screen.getByLabelText('Usuario'), usuario);
  await usuarioEvento.type(screen.getByLabelText('Contraseña'), password);
  await usuarioEvento.click(screen.getByRole('button', { name: 'Ingresar' }));
}

beforeEach(() => {
  borrarSesion();
  vi.mocked(solicitarUsuarioActual)
    .mockReset()
    .mockRejectedValue(new Error('No hay sesión que verificar.'));
  iniciarSesionApiMock.mockReset();
});

describe('LoginPage', () => {
  it('inicia sesión contra la API y entra al inicio del rol', async () => {
    iniciarSesionApiMock.mockResolvedValueOnce({ token: 'jwt-real', rol: 'DUENIO' });

    renderizarLogin();
    await completarFormulario('ana', 'secreta');

    expect(await screen.findByRole('heading', { name: 'Panel' })).toBeInTheDocument();
    expect(iniciarSesionApiMock).toHaveBeenCalledWith({
      username: 'ana',
      password: 'secreta',
    });
    expect(leerSesion()).toEqual({ token: 'jwt-real', rol: 'DUENIO', usuario: 'ana' });
  });

  it('anima la huellita mientras procesa el inicio de sesión', async () => {
    let completarInicio: (sesion: { token: string; rol: 'DUENIO' }) => void = () => {
      throw new Error('El inicio de sesión no se inició.');
    };
    iniciarSesionApiMock.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          completarInicio = resolve;
        }),
    );
    const usuarioEvento = userEvent.setup();

    renderizarLogin();
    await usuarioEvento.type(screen.getByLabelText('Usuario'), 'ana');
    await usuarioEvento.type(screen.getByLabelText('Contraseña'), 'secreta');
    await usuarioEvento.click(screen.getByRole('button', { name: 'Ingresar' }));

    const marca = screen.getByText('Huellitas').parentElement;
    const logo = marca?.previousElementSibling;
    expect(logo?.className).toContain('logoIngresando');
    expect(screen.getByRole('button', { name: 'Ingresando…' })).toBeDisabled();

    completarInicio({ token: 'jwt-real', rol: 'DUENIO' });
    expect(await screen.findByRole('heading', { name: 'Panel' })).toBeInTheDocument();
  });

  it('muestra el mensaje de credenciales inválidas y permite reintentar', async () => {
    iniciarSesionApiMock.mockRejectedValueOnce(new Error('Credenciales inválidas'));

    renderizarLogin();
    await completarFormulario('ana', 'incorrecta');

    expect(await screen.findByRole('alert')).toHaveTextContent('Credenciales inválidas');
    expect(leerSesion()).toBeNull();
    expect(screen.getByRole('button', { name: 'Ingresar' })).toBeEnabled();
  });
});
