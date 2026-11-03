import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '../../../core/api/client';
import {
  anularGastoExterno,
  crearGastoExterno,
  listarGastosExternos,
} from '../api';
import { GastosExternos } from '../pages/GastosExternos';
import type { GastoExterno } from '../tipos';

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>();

  return {
    ...actual,
    anularGastoExterno: vi.fn(),
    crearGastoExterno: vi.fn(),
    listarGastosExternos: vi.fn(),
  };
});

const GASTO: GastoExterno = {
  id: 21,
  empleado_id: null,
  empleado_nombre: '',
  descripcion: 'Castración',
  monto_centavos: 120_000,
  fecha: '2026-10-28',
  cargo_id: null,
  pago_id: null,
  registrado_por: 1,
  created_at: '2026-10-28T12:00:00',
  anulado_en: null,
  anulado_por: null,
  motivo_anulacion: null,
};

function renderizar() {
  return render(
    <MemoryRouter>
      <GastosExternos />
    </MemoryRouter>,
  );
}

function esperarListado() {
  return screen.findByRole('table', {
    name: 'Gastos a externos del período',
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(listarGastosExternos).mockResolvedValue({
    items: [GASTO],
    total_centavos: 120_000,
  });
  vi.mocked(crearGastoExterno).mockResolvedValue(GASTO);
  vi.mocked(anularGastoExterno).mockResolvedValue({
    ...GASTO,
    anulado_en: '2026-10-31T09:00:00',
    motivo_anulacion: 'Se cargó dos veces',
  });
});

describe('gastos a externos', () => {
  it('lista los gastos del período sin columna de externo', async () => {
    renderizar();

    expect(await esperarListado()).toHaveTextContent('Castración');
    expect(screen.getByText('$1.200,00')).toBeInTheDocument();
    expect(
      screen.queryByRole('columnheader', { name: 'Externo' }),
    ).not.toBeInTheDocument();
  });

  it('registra un gasto con descripción, monto y fecha', async () => {
    renderizar();

    await esperarListado();

    expect(screen.queryByLabelText('Externo (opcional)')).not.toBeInTheDocument();
    expect(
      screen.queryByText('Servicio y seña vinculados (opcional)'),
    ).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Descripción'), {
      target: { value: 'Anestesia' },
    });
    fireEvent.change(screen.getByLabelText('Monto'), {
      target: { value: '5.000' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Registrar gasto' }));

    await waitFor(() =>
      expect(crearGastoExterno).toHaveBeenCalledWith(
        {
          descripcion: 'Anestesia',
          monto_centavos: 500_000,
          fecha: expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/),
        },
        { idempotencyKey: expect.any(String) },
      ),
    );

    await waitFor(() => expect(listarGastosExternos).toHaveBeenCalledTimes(2));
  });

  it('anula un gasto con motivo obligatorio', async () => {
    renderizar();

    await esperarListado();
    fireEvent.click(screen.getByRole('button', { name: 'Anular' }));

    const dialogo = screen.getByRole('dialog', {
      name: 'Anular gasto a externo',
    });

    fireEvent.change(within(dialogo).getByLabelText('Motivo'), {
      target: { value: 'Se cargó dos veces' },
    });
    fireEvent.click(
      within(dialogo).getByRole('button', { name: 'Anular gasto' }),
    );

    await waitFor(() =>
      expect(anularGastoExterno).toHaveBeenCalledWith(21, 'Se cargó dos veces'),
    );
  });

  it('muestra el error de carga y permite reintentar', async () => {
    vi.mocked(listarGastosExternos)
      .mockRejectedValueOnce(
        new ApiError('No pudimos conectar con el servidor.', {
          tipo: 'red',
          reintentable: true,
        }),
      )
      .mockResolvedValueOnce({ items: [], total_centavos: 0 });
    renderizar();

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No pudimos conectar con el servidor.',
    );

    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }));

    expect(
      await screen.findByText('No hay gastos a externos para el período.'),
    ).toBeInTheDocument();
  });
});
