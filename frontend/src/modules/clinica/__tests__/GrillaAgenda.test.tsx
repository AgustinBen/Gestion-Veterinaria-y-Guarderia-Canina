import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { GrillaAgenda } from '../components/GrillaAgenda';
import type { AgendaDia, Turno } from '../tipos';

const TURNO: Turno = {
  id: 11,
  paciente_id: 4,
  tipo: 'CONSULTA',
  veterinario_empleado_id: 7,
  inicio: '2026-11-02T09:00:00',
  fin: '2026-11-02T09:30:00',
  estado: 'CONFIRMADO',
  motivo: null,
  atencion_id: null,
  externo_actual_id: null,
  cargo_id: null,
  created_by: 1,
  created_at: '2026-10-30T10:00:00',
};

const DIA: AgendaDia = {
  fecha: '2026-11-02',
  horarios_atencion: [],
  turnos: [TURNO],
};

describe('GrillaAgenda', () => {
  it('muestra los turnos clínicos del día y permite abrirlos', () => {
    const onAbrirTurno = vi.fn();

    render(
      <GrillaAgenda
        dia={DIA}
        nombreEmpleado={() => 'Ana Paz'}
        nombrePaciente={() => 'Luna'}
        onAbrirTurno={onAbrirTurno}
      />,
    );

    expect(
      screen.getByRole('heading', { name: 'Turnos del día' }),
    ).toBeInTheDocument();
    expect(screen.queryByText('Sin personal asignado.')).not.toBeInTheDocument();
    expect(screen.queryByText('Traspasos de turno')).not.toBeInTheDocument();
    expect(screen.getByText('Luna')).toBeInTheDocument();
    expect(screen.getByText(/Consulta/)).toBeInTheDocument();
    expect(screen.getByText('Confirmado')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Luna/ }));

    expect(onAbrirTurno).toHaveBeenCalledWith(11);
  });

  it('avisa cuando no hay turnos clínicos', () => {
    render(
      <GrillaAgenda
        dia={{ ...DIA, turnos: [] }}
        nombreEmpleado={() => 'Ana Paz'}
        nombrePaciente={() => 'Luna'}
        onAbrirTurno={vi.fn()}
      />,
    );

    expect(
      screen.getByText('No hay turnos clínicos para este día.'),
    ).toBeInTheDocument();
  });
});
