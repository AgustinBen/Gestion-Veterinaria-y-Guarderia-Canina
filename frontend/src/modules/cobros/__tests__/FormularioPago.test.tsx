import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '../../../core/api/client';
import { listarMediosPago, registrarPago } from '../api';
import { FormularioPago } from '../components/FormularioPago';
import type { CargoDetalle, MedioPago, Pago } from '../tipos';

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>();

  return {
    ...actual,
    listarMediosPago: vi.fn(),
    registrarPago: vi.fn(),
  };
});

const MEDIOS: MedioPago[] = [
  { id: 1, codigo: 'EFECTIVO', nombre: 'Efectivo', activo: true },
  { id: 2, codigo: 'TRANSFERENCIA', nombre: 'Transferencia', activo: true },
  { id: 3, codigo: 'MERCADO_PAGO', nombre: 'Mercado Pago', activo: false },
];

const CARGO: CargoDetalle = {
  id: 12,
  persona_id: 3,
  paciente_id: null,
  concepto: 'Guardería día',
  total_inicial: 10000,
  origen: 'NORMAL',
  referencia_tipo: null,
  referencia_id: null,
  creado_por: 1,
  created_at: '2026-10-20T10:00:00',
  total_vigente: 10000,
  total_pagado: 2000,
  saldo: 8000,
};

const PAGO: Pago = {
  id: 40,
  cargo_id: 12,
  monto: 8000,
  tipo: 'PAGO',
  pago_revertido_id: null,
  medio_pago_id: 1,
  es_sena: false,
  fecha: '2026-10-28',
  usuario_id: 1,
  empleado_id: null,
  clave_idempotencia: 'clave',
  created_at: '2026-10-28T10:00:00',
};

function renderizar(onPagado = vi.fn(), onCancelar = vi.fn()) {
  render(
    <FormularioPago
      cargo={CARGO}
      onCancelar={onCancelar}
      onEnviandoChange={vi.fn()}
      onPagado={onPagado}
    />,
  );

  return { onPagado, onCancelar };
}

beforeEach(() => {
  vi.mocked(listarMediosPago).mockReset();
  vi.mocked(registrarPago).mockReset();
  vi.mocked(listarMediosPago).mockResolvedValue(MEDIOS);
});

describe('FormularioPago', () => {
  it('sugiere el saldo pendiente y lista los medios de pago', async () => {
    renderizar();

    const monto = await screen.findByLabelText('Monto');
    const medio = screen.getByLabelText('Medio de pago');

    expect(monto).toHaveValue('80,00');
    expect(screen.getByText('$80,00')).toBeInTheDocument();
    expect(medio).toHaveValue('EFECTIVO');
    expect(screen.getByRole('option', { name: 'Transferencia' })).toBeEnabled();
    expect(screen.getByRole('option', { name: 'Mercado Pago' })).toBeDisabled();
    expect(screen.getByLabelText('Es seña')).not.toBeChecked();
  });

  it('registra el pago con la Idempotency-Key de la apertura y avisa el éxito', async () => {
    vi.mocked(registrarPago).mockResolvedValue(PAGO);
    const onPagado = vi.fn();
    renderizar(onPagado);

    fireEvent.change(await screen.findByLabelText('Monto'), { target: { value: '5.000,50' } });
    fireEvent.change(screen.getByLabelText('Medio de pago'), {
      target: { value: 'TRANSFERENCIA' },
    });
    fireEvent.click(screen.getByLabelText('Es seña'));
    fireEvent.click(screen.getByRole('button', { name: 'Registrar pago' }));

    await waitFor(() => expect(onPagado).toHaveBeenCalledWith(PAGO));
    expect(registrarPago).toHaveBeenCalledTimes(1);

    const [cargoId, datos, opciones] = vi.mocked(registrarPago).mock.calls[0]!;

    expect(cargoId).toBe(12);
    expect(datos).toEqual({
      monto_centavos: 500050,
      medio: 'TRANSFERENCIA',
      es_sena: true,
    });
    expect(opciones.idempotencyKey).toMatch(/\S+/);
  });

  it('reutiliza la misma Idempotency-Key al reintentar después de un error de red', async () => {
    vi.mocked(registrarPago)
      .mockRejectedValueOnce(
        new ApiError('No pudimos conectar con el servidor.', {
          tipo: 'red',
          reintentable: true,
        }),
      )
      .mockResolvedValueOnce(PAGO);
    const onPagado = vi.fn();
    renderizar(onPagado);

    const boton = await screen.findByRole('button', { name: 'Registrar pago' });
    fireEvent.click(boton);

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No pudimos conectar con el servidor.',
    );

    fireEvent.click(screen.getByRole('button', { name: 'Registrar pago' }));
    await waitFor(() => expect(onPagado).toHaveBeenCalledWith(PAGO));

    const llamadas = vi.mocked(registrarPago).mock.calls;

    expect(llamadas).toHaveLength(2);
    expect(llamadas[0]![2].idempotencyKey).toBe(llamadas[1]![2].idempotencyKey);
  });

  it('frena el doble envío con un clic repetido', async () => {
    vi.mocked(registrarPago).mockReturnValue(new Promise<Pago>(() => undefined));
    renderizar();

    const boton = await screen.findByRole('button', { name: 'Registrar pago' });
    fireEvent.click(boton);
    fireEvent.click(boton);

    await waitFor(() => expect(registrarPago).toHaveBeenCalledTimes(1));
    expect(screen.getByRole('button', { name: 'Procesando…' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Cancelar' })).toBeDisabled();
  });

  it('muestra el saldo restante cuando la API rechaza por saldo insuficiente', async () => {
    vi.mocked(registrarPago).mockRejectedValue(
      new ApiError('Saldo insuficiente. Saldo restante: 5000', {
        tipo: 'http',
        estado: 422,
        detalle: 'Saldo insuficiente. Saldo restante: 5000',
      }),
    );
    renderizar();

    fireEvent.change(await screen.findByLabelText('Monto'), { target: { value: '120' } });
    fireEvent.click(screen.getByRole('button', { name: 'Registrar pago' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'El pago supera el saldo. Saldo restante: $50,00.',
    );
  });

  it('valida el monto antes de llamar a la API', async () => {
    renderizar();

    fireEvent.change(await screen.findByLabelText('Monto'), { target: { value: '0' } });
    fireEvent.click(screen.getByRole('button', { name: 'Registrar pago' }));

    expect(screen.getByText('El monto debe ser mayor a cero.')).toBeInTheDocument();
    expect(registrarPago).not.toHaveBeenCalled();
  });

  it('muestra el error de medios de pago y permite reintentar', async () => {
    vi.mocked(listarMediosPago)
      .mockRejectedValueOnce(new ApiError('No pudimos conectar.', { tipo: 'red' }))
      .mockResolvedValueOnce(MEDIOS);
    renderizar();

    expect(await screen.findByRole('alert')).toHaveTextContent('No pudimos conectar.');

    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }));

    expect(await screen.findByLabelText('Monto')).toBeInTheDocument();
    expect(listarMediosPago).toHaveBeenCalledTimes(2);
  });
});
