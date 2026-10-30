import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { listarDeudores } from '../api';
import type { Deudor } from '../tipos';
import { useContadorDeudores } from '../useContadorDeudores';

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>();

  return {
    ...actual,
    listarDeudores: vi.fn(),
  };
});

const DEUDOR: Deudor = {
  persona: {
    id: 3,
    nombre: 'Ana',
    apellido: 'Paz',
    telefono_principal: '1144556677',
  },
  saldo_total_centavos: 123456,
  cantidad_cargos_pendientes: 2,
  deuda_mas_antigua: '2026-03-05',
  saldo_migracion_centavos: 0,
};

beforeEach(() => {
  vi.mocked(listarDeudores).mockReset();
  vi.mocked(listarDeudores).mockResolvedValue([]);
});

describe('useContadorDeudores', () => {
  it('no consulta si la sección no está en el menú', () => {
    const { result } = renderHook(() =>
      useContadorDeudores(false, '/padron'),
    );

    expect(result.current).toBeNull();
    expect(listarDeudores).not.toHaveBeenCalled();
  });

  it('devuelve la cantidad de clientes con deuda', async () => {
    vi.mocked(listarDeudores).mockResolvedValue([DEUDOR]);
    const { result } = renderHook(() =>
      useContadorDeudores(true, '/padron'),
    );

    await waitFor(() => expect(result.current).toBe(1));
    expect(listarDeudores).toHaveBeenCalledWith(
      expect.objectContaining({ orden: 'monto', limite: 100 }),
    );
  });

  it('devuelve 0 cuando no hay deudores', async () => {
    const { result } = renderHook(() =>
      useContadorDeudores(true, '/padron'),
    );

    await waitFor(() => expect(result.current).toBe(0));
  });

  it('no muestra número si la API falla', async () => {
    vi.mocked(listarDeudores).mockRejectedValue(new Error('Sin red'));
    const { result } = renderHook(() =>
      useContadorDeudores(true, '/padron'),
    );

    await waitFor(() => expect(listarDeudores).toHaveBeenCalledTimes(1));
    expect(result.current).toBeNull();
  });

  it('vuelve a consultar al cambiar de ruta', async () => {
    vi.mocked(listarDeudores)
      .mockResolvedValueOnce([DEUDOR])
      .mockResolvedValueOnce([]);
    const { result, rerender } = renderHook(
      ({ ruta }: { ruta: string }) => useContadorDeudores(true, ruta),
      { initialProps: { ruta: '/padron' } },
    );

    await waitFor(() => expect(result.current).toBe(1));

    rerender({ ruta: '/cobros' });

    await waitFor(() => expect(result.current).toBe(0));
    expect(listarDeudores).toHaveBeenCalledTimes(2);
  });
});
