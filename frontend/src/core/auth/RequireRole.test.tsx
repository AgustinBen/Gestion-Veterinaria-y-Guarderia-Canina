import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';

import { AuthProvider } from './AuthContext';
import { borrarSesion, guardarSesion } from './almacenSesion';
import { RequireRole } from './RequireRole';

function renderizar(ruta: string) {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={[ruta]}>
        <Routes>
          <Route path="/login" element={<h1>Login</h1>} />
          <Route path="/sin-acceso" element={<h1>Sin acceso</h1>} />
          <Route
            path="/panel"
            element={
              <RequireRole seccion="panel">
                <h1>Panel</h1>
              </RequireRole>
            }
          />
          <Route
            path="/padron"
            element={
              <RequireRole seccion="padron" nivel="escritura">
                <h1>Padrón editable</h1>
              </RequireRole>
            }
          />
          <Route
            path="/guarderia/nueva"
            element={
              <RequireRole seccion="nueva-reserva">
                <h1>Nueva reserva</h1>
              </RequireRole>
            }
          />
        </Routes>
      </MemoryRouter>
    </AuthProvider>,
  );
}

beforeEach(() => {
  borrarSesion();
});

describe('RequireRole', () => {
  it('sin sesión redirige a login', async () => {
    renderizar('/panel');

    expect(await screen.findByRole('heading', { name: 'Login' })).toBeInTheDocument();
  });

  it.each(['PERSONAL', 'VETERINARIO'] as const)(
    '%s en una ruta de DUENIO termina en sin acceso',
    async (rol) => {
      guardarSesion({ token: 'token-test', rol, usuario: 'Prueba' });

      renderizar('/panel');

      expect(await screen.findByRole('heading', { name: 'Sin acceso' })).toBeInTheDocument();
    },
  );

  it('DUENIO puede entrar a Panel', async () => {
    guardarSesion({ token: 'token-test', rol: 'DUENIO', usuario: 'Prueba' });

    renderizar('/panel');

    expect(await screen.findByRole('heading', { name: 'Panel' })).toBeInTheDocument();
  });

  it('VETERINARIO no puede escribir en padrón', async () => {
    guardarSesion({ token: 'token-test', rol: 'VETERINARIO', usuario: 'Prueba' });

    renderizar('/padron');

    expect(await screen.findByRole('heading', { name: 'Sin acceso' })).toBeInTheDocument();
  });

  it('PERSONAL puede escribir en padrón', async () => {
    guardarSesion({ token: 'token-test', rol: 'PERSONAL', usuario: 'Prueba' });

    renderizar('/padron');

    expect(await screen.findByRole('heading', { name: 'Padrón editable' })).toBeInTheDocument();
  });

  it('VETERINARIO no puede crear una reserva', async () => {
    guardarSesion({ token: 'token-test', rol: 'VETERINARIO', usuario: 'Prueba' });

    renderizar('/guarderia/nueva');

    expect(await screen.findByRole('heading', { name: 'Sin acceso' })).toBeInTheDocument();
  });

  it('PERSONAL puede crear una reserva', async () => {
    guardarSesion({ token: 'token-test', rol: 'PERSONAL', usuario: 'Prueba' });

    renderizar('/guarderia/nueva');

    expect(await screen.findByRole('heading', { name: 'Nueva reserva' })).toBeInTheDocument();
  });
});
