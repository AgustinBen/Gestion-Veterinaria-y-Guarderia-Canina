import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '../../../core/api/client';
import {
  anularEgreso,
  crearEgreso,
  listarCategoriasEgreso,
  listarEgresos,
} from '../api';
import { Egresos } from '../pages/Egresos';
import type { CategoriaEgreso, Egreso } from '../tipos';

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>();

  return {
    ...actual,
    anularEgreso: vi.fn(),
    crearEgreso: vi.fn(),
    listarCategoriasEgreso: vi.fn(),
    listarEgresos: vi.fn(),
  };
});

const CATEGORIAS: CategoriaEgreso[] = [
  { id: 3, nombre: 'Insumos', activa: true },
  { id: 4, nombre: 'Servicios', activa: false },
];

const EGRESO: Egreso = {
  id: 11,
  fecha: '2026-10-30',
  monto_centavos: 45_000,
  categoria_id: 3,
  categoria_nombre: 'Insumos',
  descripcion: 'Alimento balanceado',
  medio_pago_id: null,
  registrado_por: 1,
  created_at: '2026-10-30T10:00:00',
  anulado_en: null,
  anulado_por: null,
  motivo_anulacion: null,
};

function renderizar() {
  return render(
    <MemoryRouter>
      <Egresos />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(listarCategoriasEgreso).mockResolvedValue(CATEGORIAS);
  vi.mocked(listarEgresos).mockResolvedValue([EGRESO]);
  vi.mocked(crearEgreso).mockResolvedValue(EGRESO);
  vi.mocked(anularEgreso).mockResolvedValue({
    ...EGRESO,
    anulado_en: '2026-10-31T09:00:00',
    motivo_anulacion: 'Error de carga',
  });
});

describe('egresos operativos', () => {
  it('avisa que primero hace falta una categoría y bloquea el alta', async () => {
    vi.mocked(listarCategoriasEgreso).mockResolvedValue([]);
    vi.mocked(listarEgresos).mockResolvedValue([]);
    renderizar();

    expect(
      await screen.findByText(/Todavía no hay categorías de egreso/),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Registrar egreso' })).toBeDisabled();
  });

  it('registra un egreso con monto en centavos y clave de idempotencia', async () => {
    renderizar();

    expect(await screen.findByText('Alimento balanceado')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Monto'), {
      target: { value: '10.000,50' },
    });
    fireEvent.change(screen.getByLabelText('Descripción'), {
      target: { value: '  Vacunas  ' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Registrar egreso' }));

    await waitFor(() =>
      expect(crearEgreso).toHaveBeenCalledWith(
        {
          fecha: expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/),
          monto_centavos: 1_000_050,
          categoria_id: 3,
          descripcion: 'Vacunas',
        },
        { idempotencyKey: expect.any(String) },
      ),
    );

    await waitFor(() => expect(listarEgresos).toHaveBeenCalledTimes(2));
    expect(screen.getByLabelText('Monto')).toHaveValue('');
    expect(screen.getByLabelText('Descripción')).toHaveValue('');
  });

  it('muestra el error del backend sin romper el formulario', async () => {
    vi.mocked(crearEgreso).mockRejectedValueOnce(
      new ApiError('El monto debe ser mayor a cero.', { tipo: 'respuesta' }),
    );
    renderizar();

    await screen.findByText('Alimento balanceado');

    fireEvent.change(screen.getByLabelText('Monto'), {
      target: { value: '1.000' },
    });
    fireEvent.change(screen.getByLabelText('Descripción'), {
      target: { value: 'Algo' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Registrar egreso' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'El monto debe ser mayor a cero.',
    );
  });

  it('exige un motivo para anular y luego anula el egreso', async () => {
    renderizar();

    await screen.findByText('Alimento balanceado');
    fireEvent.click(screen.getByRole('button', { name: 'Anular' }));

    const dialogo = screen.getByRole('dialog', { name: 'Anular egreso' });

    fireEvent.click(
      within(dialogo).getByRole('button', { name: 'Anular egreso' }),
    );

    expect(within(dialogo).getByText('El motivo es obligatorio.')).toBeInTheDocument();
    expect(anularEgreso).not.toHaveBeenCalled();

    fireEvent.change(within(dialogo).getByLabelText('Motivo'), {
      target: { value: 'Error de carga' },
    });
    fireEvent.click(
      within(dialogo).getByRole('button', { name: 'Anular egreso' }),
    );

    await waitFor(() =>
      expect(anularEgreso).toHaveBeenCalledWith(11, 'Error de carga'),
    );
    await waitFor(() =>
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument(),
    );
  });

  it('muestra el error de carga y permite reintentar', async () => {
    vi.mocked(listarEgresos)
      .mockRejectedValueOnce(
        new ApiError('No pudimos conectar con el servidor.', {
          tipo: 'red',
          reintentable: true,
        }),
      )
      .mockResolvedValueOnce([]);
    renderizar();

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No pudimos conectar con el servidor.',
    );

    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }));

    expect(
      await screen.findByText('No hay egresos registrados para el período.'),
    ).toBeInTheDocument();
  });
});
