import { fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { AuthContext } from '../../../core/auth/contexto';
import type { Rol } from '../../../core/auth/permisos';
import { Calendario } from '../pages/Calendario';

function renderizarCalendario(rol: Rol) {
  return render(
    <AuthContext.Provider
      value={{
        sesion: { token: 'token-test', rol, usuario: 'Prueba' },
        iniciarSesion: async () => undefined,
        cerrarSesion: () => undefined,
      }}
    >
      <MemoryRouter>
        <Calendario />
      </MemoryRouter>
    </AuthContext.Provider>,
  );
}

describe('Calendario de guardería', () => {
  it('muestra la agenda y permite cambiar el mes y la fecha seleccionada', () => {
    renderizarCalendario('PERSONAL');

    const calendario = screen.getByRole('region', { name: 'Calendario mensual' });
    const encabezadoMes = within(calendario).getByRole('heading', { level: 2 });
    const mesActual = encabezadoMes.textContent;

    expect(screen.getByRole('heading', { name: 'Calendario de agenda' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Reservas de guardería' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Turnos clínicos' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Nueva reserva' })).toHaveAttribute(
      'href',
      '/guarderia/nueva',
    );

    fireEvent.click(screen.getByRole('button', { name: 'Mes siguiente' }));
    expect(encabezadoMes.textContent).not.toBe(mesActual);

    const diaPrimero = screen.getByRole('button', { name: /^1 de / });
    fireEvent.click(diaPrimero);
    expect(diaPrimero).toHaveAttribute('aria-pressed', 'true');
  });

  it('mantiene la vista de solo lectura para veterinaria', () => {
    renderizarCalendario('VETERINARIO');

    expect(screen.getByText('Solo lectura')).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Nueva reserva' })).not.toBeInTheDocument();
  });
});
