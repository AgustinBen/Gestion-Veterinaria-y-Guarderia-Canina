import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError, api } from '../../../core/api/client';
import {
  crearReserva,
  leerErrorReserva,
  listarCalendario,
  obtenerReserva,
  registrarSena,
} from '../api';
import type { ReservaCrear } from '../tipos';

vi.mock('../../../core/api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../../core/api/client')>();

  return {
    ...actual,
    api: {
      get: vi.fn(),
      post: vi.fn(),
    },
  };
});

const SOLICITUD: ReservaCrear = {
  tutor_persona_id: 8,
  paciente_ids: [12, 14],
  desde_fecha: '2026-12-15',
  desde_franja: 'DIA',
  hasta_fecha: '2026-12-15',
  hasta_franja: 'NOCHE',
  cuidados_extras: [
    { paciente_id: 12, cuidados_extras: false },
    {
      paciente_id: 14,
      cuidados_extras: true,
      tipo_cuidado: 'Administrar medicación',
    },
  ],
  total_centavos: 250000,
};

beforeEach(() => {
  vi.mocked(api.get).mockReset();
  vi.mocked(api.post).mockReset();
});

describe('API de guardería', () => {
  it('consulta calendario con las fechas del rango', () => {
    listarCalendario('2026-12-14', '2026-12-20');

    expect(api.get).toHaveBeenCalledWith(
      '/guarderia/calendario?desde=2026-12-14&hasta=2026-12-20',
      { signal: undefined },
    );
  });

  it('envía la reserva estructurada y la clave idempotente', () => {
    crearReserva(SOLICITUD, { idempotencyKey: 'clave-formulario' });

    expect(api.post).toHaveBeenCalledWith('/guarderia/reservas', SOLICITUD, {
      idempotencyKey: 'clave-formulario',
      signal: undefined,
    });
  });

  it('registra la seña en centavos con la misma clave del formulario', () => {
    registrarSena(
      42,
      { monto_centavos: 5000, medio: 'EFECTIVO' },
      { idempotencyKey: 'clave-formulario' },
    );

    expect(api.post).toHaveBeenCalledWith(
      '/guarderia/reservas/42/sena',
      { monto_centavos: 5000, medio: 'EFECTIVO' },
      { idempotencyKey: 'clave-formulario', signal: undefined },
    );
  });

  it('obtiene el detalle por id', () => {
    obtenerReserva(42);

    expect(api.get).toHaveBeenCalledWith('/guarderia/reservas/42', {
      signal: undefined,
    });
  });

  it('interpreta los conflictos de cupo y descarta datos mal formados', () => {
    const error = new ApiError('Conflicto', {
      tipo: 'http',
      estado: 409,
      detalle: {
        codigo: 'SIN_CUPO',
        franjas_sin_lugar: [
          {
            fecha: '2026-12-15',
            franja: 'NOCHE',
            necesita: 1,
            disponible: 0,
          },
          { fecha: 'inválida', franja: 'DIA' },
        ],
        ocupaciones_existentes: [],
      },
    });

    expect(leerErrorReserva(error)).toEqual({
      codigo: 'SIN_CUPO',
      franjas_sin_lugar: [
        {
          fecha: '2026-12-15',
          franja: 'NOCHE',
          necesita: 1,
          disponible: 0,
        },
      ],
      ocupaciones_existentes: [],
    });
  });
});
