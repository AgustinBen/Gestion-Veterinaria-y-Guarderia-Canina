import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '../../../core/auth/AuthContext';
import { guardarSesion } from '../../../core/auth/almacenSesion';
import type { Rol } from '../../../core/auth/permisos';
import { ajustarPrecio } from '../api';
import { DialogoAjuste } from '../components/DialogoAjuste';
import type { AjustePrecio, CargoDetalle } from '../tipos';

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>();

  return {
    ...actual,
    ajustarPrecio: vi.fn(),
  };
});

vi.mock('../../../core/auth/servicioAuth', () => ({
  iniciarSesionApi: vi.fn(),
  cerrarSesionApi: vi.fn().mockResolvedValue(undefined),
  solicitarUsuarioActual: vi
    .fn()
    .mockRejectedValue(new Error('La verificación de sesión no aplica en este test.')),
}));

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

const AJUSTE: AjustePrecio = {
  id: 5,
  cargo_id: 12,
  precio_anterior: 10000,
  precio_nuevo: 12000,
  motivo: 'Ajuste acordado',
  usuario_id: 1,
  created_at: '2026-10-28T10:00:00',
};

function renderizar(rol: Rol, onAjustado = vi.fn()) {
  guardarSesion({ token: 'token-test', rol, usuario: 'Prueba' });

  render(
    <AuthProvider>
      <DialogoAjuste
        abierto
        cargo={CARGO}
        onAjustado={onAjustado}
        onCerrar={vi.fn()}
      />
    </AuthProvider>,
  );

  return { onAjustado };
}

function completar(nuevoTotal: string, motivo = 'Ajuste acordado') {
  fireEvent.change(screen.getByLabelText('Precio nuevo'), {
    target: { value: nuevoTotal },
  });
  fireEvent.change(screen.getByLabelText('Motivo'), { target: { value: motivo } });
}

beforeEach(() => {
  vi.mocked(ajustarPrecio).mockReset();
});

describe('DialogoAjuste', () => {
  it('arranca con el precio actual y exige un cambio y un motivo', () => {
    renderizar('DUENIO');

    expect(screen.getByLabelText('Precio nuevo')).toHaveValue('100,00');
    expect(screen.getByText('$100,00')).toBeInTheDocument();
    expect(screen.getByText('$20,00')).toBeInTheDocument();
    expect(screen.getByText('El precio nuevo debe ser distinto del actual.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Continuar' })).toBeDisabled();
  });

  it('no deja continuar sin motivo', () => {
    renderizar('DUENIO');

    fireEvent.change(screen.getByLabelText('Precio nuevo'), { target: { value: '120' } });

    expect(screen.getByRole('button', { name: 'Continuar' })).toBeDisabled();

    fireEvent.change(screen.getByLabelText('Motivo'), { target: { value: 'Ajuste' } });

    expect(screen.getByRole('button', { name: 'Continuar' })).toBeEnabled();
  });

  it('bloquea un precio nuevo menor a lo ya pagado', () => {
    renderizar('DUENIO');

    completar('10');

    expect(
      screen.getByText(/El precio nuevo no puede ser menor a lo ya pagado/),
    ).toHaveTextContent('$20,00');
    expect(screen.getByRole('button', { name: 'Continuar' })).toBeDisabled();
  });

  it('PERSONAL puede subir el precio: pide confirmación y envía el ajuste', async () => {
    vi.mocked(ajustarPrecio).mockResolvedValue(AJUSTE);
    const { onAjustado } = renderizar('PERSONAL');

    completar('120');
    fireEvent.click(screen.getByRole('button', { name: 'Continuar' }));

    expect(screen.getByText('Precio nuevo')).toBeInTheDocument();
    expect(screen.getByText('$120,00')).toBeInTheDocument();
    expect(screen.getByText('Ajuste acordado')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Confirmar ajuste' }));

    await waitFor(() => expect(onAjustado).toHaveBeenCalledWith(AJUSTE));
    expect(ajustarPrecio).toHaveBeenCalledWith(12, {
      nuevo_total_centavos: 12000,
      motivo: 'Ajuste acordado',
    });
  });

  it('PERSONAL no puede bajar el precio', () => {
    renderizar('PERSONAL');

    completar('90');

    expect(
      screen.getByText(/Bajar el precio solo lo puede hacer el Dueño/),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Continuar' })).toBeDisabled();
    expect(ajustarPrecio).not.toHaveBeenCalled();
  });

  it('DUENIO puede bajar el precio con motivo', async () => {
    vi.mocked(ajustarPrecio).mockResolvedValue({
      ...AJUSTE,
      precio_nuevo: 9000,
      motivo: 'Descuento cliente frecuente',
    });
    const { onAjustado } = renderizar('DUENIO');

    completar('90', 'Descuento cliente frecuente');
    fireEvent.click(screen.getByRole('button', { name: 'Continuar' }));
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar ajuste' }));

    await waitFor(() => expect(onAjustado).toHaveBeenCalled());
    expect(ajustarPrecio).toHaveBeenCalledWith(12, {
      nuevo_total_centavos: 9000,
      motivo: 'Descuento cliente frecuente',
    });
  });

  it('muestra el error del backend sin cerrar el diálogo', async () => {
    vi.mocked(ajustarPrecio).mockRejectedValue(new Error('No tenés permiso.'));
    renderizar('DUENIO');

    completar('120');
    fireEvent.click(screen.getByRole('button', { name: 'Continuar' }));
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar ajuste' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('No tenés permiso.');
    expect(screen.getByRole('button', { name: 'Confirmar ajuste' })).toBeInTheDocument();
  });
});
