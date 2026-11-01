import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '../auth/AuthContext';
import { borrarSesion, guardarSesion } from '../auth/almacenSesion';
import { solicitarUsuarioActual } from '../auth/servicioAuth';
import { PantallaProvisoria } from './PantallaProvisoria';

vi.mock('../auth/servicioAuth', () => ({
  iniciarSesionApi: vi.fn(),
  cerrarSesionApi: vi.fn().mockResolvedValue(undefined),
  solicitarUsuarioActual: vi.fn(),
}));

beforeEach(() => {
  borrarSesion();
  guardarSesion({ token: 'token-test', rol: 'DUENIO', usuario: 'Prueba' });
  vi.mocked(solicitarUsuarioActual).mockRejectedValue(
    new Error('La verificación de sesión no aplica en este test.'),
  );
});

describe('PantallaProvisoria', () => {
  it('muestra las opciones Mensual y Anual del resumen del Panel', () => {
    render(
      <AuthProvider>
        <MemoryRouter>
          <PantallaProvisoria
            seccion="panel"
            titulo="Panel"
            descripcion="Resumen del negocio."
          />
        </MemoryRouter>
      </AuthProvider>,
    );

    const periodos = screen.getByLabelText('Períodos del resumen');

    expect(within(periodos).getByText('Mensual')).toBeInTheDocument();
    expect(within(periodos).getByText('Anual')).toBeInTheDocument();
    expect(within(periodos).queryByText('Resumen mensual')).not.toBeInTheDocument();
    const metricas = screen.getByRole('region', { name: 'Métricas del negocio' });

    expect(within(metricas).getByRole('heading', { name: 'Métricas del negocio' })).toBeInTheDocument();
    expect(within(metricas).queryByText('Panel del dueño')).not.toBeInTheDocument();
  });
});
