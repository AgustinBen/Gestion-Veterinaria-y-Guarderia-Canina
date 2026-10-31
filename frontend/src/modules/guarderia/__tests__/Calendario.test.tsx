import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { listarCalendario } from '../api';
import { Calendario } from '../pages/Calendario';
import type { Disponibilidad } from '../tipos';

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>();

  return { ...actual, listarCalendario: vi.fn() };
});

vi.mock('../permisos', () => ({
  usePuedeEscribirReservas: vi.fn(() => true),
}));

function disponibilidad(
  franja: 'DIA' | 'NOCHE',
  disponible: number,
  fecha = '2026-12-14',
): Disponibilidad {
  return {
    fecha,
    franja,
    cupo_maximo: 6,
    plazas_emergencia: 3,
    habilitadas: 0,
    publico: 3,
    ocupado: 3 - disponible,
    disponible,
  };
}

function renderizar() {
  return render(
    <MemoryRouter>
      <Calendario />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.setSystemTime(new Date(2026, 11, 14, 12));
  vi.mocked(listarCalendario).mockReset();
  vi.mocked(listarCalendario).mockResolvedValue([
    disponibilidad('DIA', 1),
    disponibilidad('NOCHE', 0),
  ]);
});

describe('Calendario', () => {
  it('muestra el mes completo y la ocupación de Día y Noche con el cupo público', async () => {
    renderizar();

    expect(await screen.findByRole('button', { name: /Día: 2 ocupadas de 3, Con lugar/i }))
      .toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Noche: 3 ocupadas de 3, Completo/i }))
      .toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: /Reservar/ })).toHaveLength(31);
    expect(screen.getByRole('heading', { name: 'diciembre de 2026' })).toBeInTheDocument();
  });

  it('al tocar un chip muestra ocupación, plazas de emergencia y habilitaciones', async () => {
    renderizar();
    const chip = await screen.findByRole('button', { name: /Día: 2 ocupadas/ });

    fireEvent.click(chip);

    const detalle = screen.getByLabelText('Detalle Día');
    expect(detalle).toHaveTextContent('Ocupado2');
    expect(detalle).toHaveTextContent('Plazas de emergencia3');
    expect(detalle).toHaveTextContent('Habilitadas0');
  });

  it('permite navegar al mes siguiente', async () => {
    renderizar();
    await screen.findByRole('button', { name: /Día: 2 ocupadas/ });
    fireEvent.click(screen.getByRole('button', { name: 'Mes siguiente' }));

    await waitFor(() =>
      expect(listarCalendario).toHaveBeenLastCalledWith(
        '2027-01-01',
        '2027-01-31',
        expect.objectContaining({ signal: expect.any(AbortSignal) }),
      ),
    );
  });

  it('enlaza el día elegido a una nueva reserva con la fecha preseleccionada', async () => {
    renderizar();
    const fecha = await screen.findByRole('link', { name: 'Reservar 14 de diciembre' });

    expect(fecha).toHaveAttribute('href', '/guarderia/reservar?fecha=2026-12-14');
  });

  it('muestra un error de carga con opción para reintentar', async () => {
    vi.mocked(listarCalendario)
      .mockRejectedValueOnce(new Error('Sin conexión'))
      .mockResolvedValueOnce([disponibilidad('DIA', 2)]);
    renderizar();

    expect(await screen.findByRole('alert')).toHaveTextContent('Sin conexión');
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }));

    expect(await screen.findByRole('button', { name: /Día: 1 ocupadas/ })).toBeInTheDocument();
    expect(listarCalendario).toHaveBeenCalledTimes(2);
  });
});
