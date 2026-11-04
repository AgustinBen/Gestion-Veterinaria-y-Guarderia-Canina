import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { TablaCargos } from '../components/TablaCargos';
import type { CargoDetalle } from '../tipos';

const CARGO: CargoDetalle = {
  id: 12,
  persona_id: 3,
  paciente_id: null,
  concepto: 'Reserva de guardería #7',
  total_inicial: 10000,
  origen: 'NORMAL',
  referencia_tipo: 'RESERVA',
  referencia_id: 7,
  reserva_estado: null,
  creado_por: 1,
  created_at: '2026-10-20T10:00:00',
  total_vigente: 10000,
  total_pagado: 2000,
  saldo: 8000,
};

function renderTabla(cargo: CargoDetalle) {
  render(<TablaCargos cargos={[cargo]} onCobrar={vi.fn()} />);
}

describe('TablaCargos', () => {
  it('muestra CANCELADO en el cargo de una reserva cancelada', () => {
    renderTabla({ ...CARGO, reserva_estado: 'CANCELADA' });

    expect(screen.getByText('CANCELADO')).toBeInTheDocument();
  });

  it('no muestra CANCELADO en el cargo de una reserva activa', () => {
    renderTabla({ ...CARGO, reserva_estado: 'CONFIRMADA' });

    expect(screen.queryByText('CANCELADO')).not.toBeInTheDocument();
  });

  it('no muestra CANCELADO en un cargo sin reserva vinculada', () => {
    renderTabla({
      ...CARGO,
      concepto: 'Consulta',
      referencia_tipo: null,
      referencia_id: null,
    });

    expect(screen.queryByText('CANCELADO')).not.toBeInTheDocument();
  });
});
