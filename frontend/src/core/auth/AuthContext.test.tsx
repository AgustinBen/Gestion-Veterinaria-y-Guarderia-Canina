import { act, renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AuthProvider } from './AuthContext';
import {
  borrarSesion,
  guardarSesion,
  leerSesion,
  notificarSesionExpirada,
} from './almacenSesion';
import { useAuth } from './contexto';
import { cerrarSesionApi, iniciarSesionApi, solicitarUsuarioActual } from './servicioAuth';

vi.mock('./servicioAuth', () => ({
  iniciarSesionApi: vi.fn(),
  cerrarSesionApi: vi.fn(),
  solicitarUsuarioActual: vi.fn(),
}));

const iniciarSesionApiMock = vi.mocked(iniciarSesionApi);
const cerrarSesionApiMock = vi.mocked(cerrarSesionApi);
const solicitarUsuarioActualMock = vi.mocked(solicitarUsuarioActual);

function envolver({ children }: { children: ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}

beforeEach(() => {
  borrarSesion();
  iniciarSesionApiMock.mockReset();
  cerrarSesionApiMock.mockReset().mockResolvedValue(undefined);
  solicitarUsuarioActualMock
    .mockReset()
    .mockRejectedValue(new Error('La verificación de sesión no aplica en este test.'));
});

describe('AuthProvider', () => {
  it('guarda el token y el rol que devuelve el backend', async () => {
    iniciarSesionApiMock.mockResolvedValueOnce({ token: 'jwt-real', rol: 'VETERINARIO' });

    const { result } = renderHook(() => useAuth(), { wrapper: envolver });

    await act(async () => {
      await result.current.iniciarSesion({ usuario: '  ana ', password: 'secreta' });
    });

    expect(iniciarSesionApiMock).toHaveBeenCalledWith({
      username: 'ana',
      password: 'secreta',
    });
    expect(result.current.sesion).toEqual({
      token: 'jwt-real',
      rol: 'VETERINARIO',
      usuario: 'ana',
    });
    expect(leerSesion()).toEqual(result.current.sesion);
  });

  it('no guarda sesión cuando el backend rechaza las credenciales', async () => {
    iniciarSesionApiMock.mockRejectedValueOnce(new Error('Credenciales inválidas'));

    const { result } = renderHook(() => useAuth(), { wrapper: envolver });

    await act(async () => {
      await expect(
        result.current.iniciarSesion({ usuario: 'ana', password: 'incorrecta' }),
      ).rejects.toThrow('Credenciales inválidas');
    });

    expect(result.current.sesion).toBeNull();
    expect(leerSesion()).toBeNull();
  });

  it('valida usuario y contraseña antes de llamar a la API', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper: envolver });

    await act(async () => {
      await expect(
        result.current.iniciarSesion({ usuario: '   ', password: '' }),
      ).rejects.toThrow('Ingresá usuario y contraseña.');
    });

    expect(iniciarSesionApiMock).not.toHaveBeenCalled();
  });

  it('al cerrar sesión limpia el almacenamiento y avisa al backend', async () => {
    guardarSesion({ token: 'jwt-real', rol: 'PERSONAL', usuario: 'ana' });

    const { result } = renderHook(() => useAuth(), { wrapper: envolver });

    await waitFor(() => expect(solicitarUsuarioActualMock).toHaveBeenCalledTimes(1));

    act(() => {
      result.current.cerrarSesion();
    });

    expect(cerrarSesionApiMock).toHaveBeenCalledWith('jwt-real');
    expect(result.current.sesion).toBeNull();
    expect(leerSesion()).toBeNull();
  });

  it('sincroniza el rol y el usuario vigentes al reabrir la app', async () => {
    guardarSesion({ token: 'jwt-real', rol: 'PERSONAL', usuario: 'viejo' });
    solicitarUsuarioActualMock.mockResolvedValueOnce({
      id: 7,
      username: 'ana',
      rol: 'DUENIO',
      empleado_id: null,
    });

    const { result } = renderHook(() => useAuth(), { wrapper: envolver });

    await waitFor(() => {
      expect(result.current.sesion).toEqual({
        token: 'jwt-real',
        rol: 'DUENIO',
        usuario: 'ana',
      });
    });
  });

  it('reacciona al evento de sesión expirada que emite el cliente API', async () => {
    guardarSesion({ token: 'jwt-vencido', rol: 'DUENIO', usuario: 'ana' });

    const { result } = renderHook(() => useAuth(), { wrapper: envolver });

    act(() => {
      notificarSesionExpirada();
    });

    await waitFor(() => expect(result.current.sesion).toBeNull());
  });
});
