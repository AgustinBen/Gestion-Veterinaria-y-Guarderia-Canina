import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AuthContext } from '../../../core/auth/contexto';
import type { Rol } from '../../../core/auth/permisos';
import {
  generarIdempotencyKey,
  habilitarPlazaEmergencia,
  listarCalendario,
  listarReservas,
} from '../api';
import { fechaLocal } from '../fechas';
import { Calendario } from '../pages/Calendario';
import type { Reserva } from '../tipos';

vi.mock('../api', () => ({
  generarIdempotencyKey: vi.fn(() => 'clave-emergencia-calendario'),
  habilitarPlazaEmergencia: vi.fn(),
  listarCalendario: vi.fn(),
  listarReservas: vi.fn(),
  mensajeDeError: (error: unknown) =>
    error instanceof Error ? error.message : 'Error desconocido',
}));

const RESERVA: Reserva = {
  id: 71,
  tutor_persona_id: 8,
  desde_fecha: '',
  desde_franja: 'DIA',
  hasta_fecha: '',
  hasta_franja: 'NOCHE',
  estado: 'CONFIRMADA',
  cargo_id: 51,
  total_centavos: 123456,
  sena_centavos: 2000,
  pacientes: [{ paciente_id: 21, cuidados_extras: false, tipo_cuidado: null }],
  created_at: '',
};

beforeEach(() => {
  vi.mocked(listarCalendario).mockReset().mockResolvedValue([]);
  vi.mocked(listarReservas).mockReset().mockResolvedValue([]);
  vi.mocked(generarIdempotencyKey).mockReset().mockReturnValue(
    'clave-emergencia-calendario',
  );
  vi.mocked(habilitarPlazaEmergencia).mockReset().mockResolvedValue({
    fecha: fechaLocal(new Date()),
    franja: 'DIA',
    cupo_maximo: 3,
    plazas_emergencia: 1,
    habilitadas: 1,
    publico: 3,
    ocupado: 0,
    disponible: 3,
  });
});

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
      `/guarderia/reservar?fecha=${fechaLocal(new Date())}`,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Mes siguiente' }));
    expect(encabezadoMes.textContent).not.toBe(mesActual);

    const diaPrimero = screen.getByRole('button', { name: /^1 de / });
    fireEvent.click(diaPrimero);
    expect(diaPrimero).toHaveAttribute('aria-pressed', 'true');
    const mesSiguiente = new Date();
    mesSiguiente.setMonth(mesSiguiente.getMonth() + 1, 1);
    const fechaEsperada = fechaLocal(
      new Date(mesSiguiente.getFullYear(), mesSiguiente.getMonth(), 1),
    );
    expect(screen.getByRole('link', { name: 'Nueva reserva' })).toHaveAttribute(
      'href',
      `/guarderia/reservar?fecha=${fechaEsperada}`,
    );
  });

  it('mantiene la vista de solo lectura para veterinaria', () => {
    renderizarCalendario('VETERINARIO');

    expect(screen.getByText('Solo lectura')).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Nueva reserva' })).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: 'Habilitar plaza de emergencia' }),
    ).not.toBeInTheDocument();
  });

  it('muestra la ocupación por franja y las reservas de la fecha seleccionada', async () => {
    const hoy = fechaLocal(new Date());
    const cupoConfigurado = 3;
    vi.mocked(listarCalendario).mockResolvedValue([
      {
        fecha: hoy,
        franja: 'DIA',
        cupo_maximo: cupoConfigurado,
        plazas_emergencia: 1,
        habilitadas: 0,
        publico: 2,
        ocupado: 1,
        disponible: 1,
      },
      {
        fecha: hoy,
        franja: 'NOCHE',
        cupo_maximo: cupoConfigurado,
        plazas_emergencia: 1,
        habilitadas: 0,
        publico: 2,
        ocupado: cupoConfigurado,
        disponible: 0,
      },
    ]);
    vi.mocked(listarReservas).mockResolvedValue([
      { ...RESERVA, desde_fecha: hoy, hasta_fecha: hoy },
      {
        ...RESERVA,
        id: 72,
        estado: 'CANCELADA',
        desde_fecha: hoy,
        hasta_fecha: hoy,
      },
    ]);

    renderizarCalendario('PERSONAL');

    expect(
      await screen.findByLabelText('Día: 1 de 3 plazas ocupadas'),
    ).toBeInTheDocument(    );
    const cupoDia = screen.getByLabelText('Día: 1 de 3 plazas ocupadas');
    const cupoNoche = screen.getByLabelText('Noche: 3 de 3 plazas ocupadas');
    expect(cupoDia).toHaveTextContent('1/3');
    expect(cupoDia.querySelector('span')?.className).toContain(
      'cupoOcupadoParcial',
    );
    expect(cupoNoche).toHaveTextContent('3/3');
    expect(cupoNoche.querySelector('span')?.className).toContain(
      'cupoOcupadoCompleto',
    );
    expect(await screen.findByRole('link', { name: 'Reserva #71' })).toHaveAttribute(
      'href',
      '/guarderia/reservas/71',
    );
    expect(screen.queryByRole('link', { name: 'Reserva #72' })).not.toBeInTheDocument();
    expect(screen.getByText(/Día · Noche/)).toBeInTheDocument();
  });

  it('permite al Dueño habilitar una plaza de emergencia para el día seleccionado', async () => {
    const hoy = fechaLocal(new Date());
    renderizarCalendario('DUENIO');

    fireEvent.click(
      await screen.findByRole('button', { name: 'Habilitar plaza de emergencia' }),
    );
    expect(screen.getByRole('region', { name: 'Calendario mensual' }))
      .toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /\d+ de / }))
      .toBeInTheDocument();
    const botonesCalendario = screen.getAllByRole('button', {
      name: /^\d+ de /,
    });
    expect(botonesCalendario.length).toBeGreaterThan(0);
    const indicadoresFranja = botonesCalendario[0]?.querySelector(
      ':scope > span',
    );
    expect(indicadoresFranja?.children).toHaveLength(2);
    fireEvent.change(screen.getByLabelText('Franja'), {
      target: { value: 'NOCHE' },
    });
    fireEvent.change(screen.getByLabelText('Motivo'), {
      target: { value: 'Necesidad operativa' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar habilitación' }));

    await waitFor(() =>
      expect(habilitarPlazaEmergencia).toHaveBeenCalledWith(
        { fecha: hoy, franja: 'NOCHE', motivo: 'Necesidad operativa' },
        { idempotencyKey: 'clave-emergencia-calendario' },
      ),
    );
    expect(screen.getByRole('region', { name: 'Calendario mensual' }))
      .toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /\d+ de / }))
      .toBeInTheDocument();
  });

  it('no ofrece habilitar emergencias al Personal', async () => {
    renderizarCalendario('PERSONAL');

    await screen.findByRole('heading', { name: 'Reservas de guardería' });
    expect(
      screen.queryByRole('button', { name: 'Habilitar plaza de emergencia' }),
    ).not.toBeInTheDocument();
  });
});
