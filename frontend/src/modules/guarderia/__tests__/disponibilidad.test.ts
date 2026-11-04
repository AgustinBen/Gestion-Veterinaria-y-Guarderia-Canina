import { describe, expect, it } from 'vitest';

import {
  cuposPublicosLibres,
  etiquetaNivel,
  nivelDisponibilidad,
} from '../disponibilidad';

const CUPO_PUBLICO_CHICO = 4;
const CUPO_PUBLICO_GRANDE = 9;
const PORCENTAJE_ESTRICTO = 10;
const PORCENTAJE_AMPLIO = 50;

type DatosDisponibilidad = {
  publico: number;
  disponible: number;
  exceso_ocupacion: number;
};

function sembrar(
  sobrescribir: Partial<DatosDisponibilidad> = {},
): DatosDisponibilidad {
  return {
    publico: CUPO_PUBLICO_CHICO,
    disponible: CUPO_PUBLICO_CHICO,
    exceso_ocupacion: 0,
    ...sobrescribir,
  };
}

describe('nivelDisponibilidad', () => {
  it('marca sin cupo cuando la API informa disponibilidad cero', () => {
    expect(
      nivelDisponibilidad(
        sembrar({ publico: CUPO_PUBLICO_CHICO, disponible: 0 }),
        PORCENTAJE_AMPLIO,
      ),
    ).toBe('sin-cupo');
    expect(
      nivelDisponibilidad(
        sembrar({ publico: CUPO_PUBLICO_GRANDE, disponible: 0 }),
        PORCENTAJE_AMPLIO,
      ),
    ).toBe('sin-cupo');
  });

  it('marca sin cupo cuando hay exceso de ocupación', () => {
    expect(
      nivelDisponibilidad(
        sembrar({ disponible: 0, exceso_ocupacion: CUPO_PUBLICO_CHICO }),
        PORCENTAJE_AMPLIO,
      ),
    ).toBe('sin-cupo');
  });

  it('marca sin datos cuando la API no informó la franja', () => {
    expect(nivelDisponibilidad(null, PORCENTAJE_AMPLIO)).toBe('sin-datos');
    expect(nivelDisponibilidad(undefined, PORCENTAJE_AMPLIO)).toBe('sin-datos');
  });

  it('marca últimas plazas en el umbral sembrado o por debajo', () => {
    expect(
      nivelDisponibilidad(
        sembrar({ publico: CUPO_PUBLICO_CHICO, disponible: 2 }),
        PORCENTAJE_AMPLIO,
      ),
    ).toBe('limitada');
    expect(
      nivelDisponibilidad(
        sembrar({ publico: CUPO_PUBLICO_GRANDE, disponible: 4 }),
        PORCENTAJE_AMPLIO,
      ),
    ).toBe('limitada');
  });

  it('marca con lugar cuando supera el umbral sembrado', () => {
    expect(
      nivelDisponibilidad(
        sembrar({ publico: CUPO_PUBLICO_CHICO, disponible: 3 }),
        PORCENTAJE_AMPLIO,
      ),
    ).toBe('libre');
    expect(
      nivelDisponibilidad(
        sembrar({ publico: CUPO_PUBLICO_GRANDE, disponible: 5 }),
        PORCENTAJE_AMPLIO,
      ),
    ).toBe('libre');
  });

  it('no depende de un porcentaje fijo: el umbral entra por parámetro', () => {
    const datos = sembrar({ publico: CUPO_PUBLICO_CHICO, disponible: 2 });

    expect(nivelDisponibilidad(datos, PORCENTAJE_ESTRICTO)).toBe('libre');
    expect(nivelDisponibilidad(datos, PORCENTAJE_AMPLIO)).toBe('limitada');
  });

  it('aplica el umbral por defecto del módulo sobre el cupo público', () => {
    expect(
      nivelDisponibilidad(sembrar({ publico: CUPO_PUBLICO_CHICO, disponible: 1 })),
    ).toBe('limitada');
    expect(
      nivelDisponibilidad(sembrar({ publico: CUPO_PUBLICO_CHICO, disponible: 2 })),
    ).toBe('libre');
    expect(
      nivelDisponibilidad(sembrar({ publico: CUPO_PUBLICO_GRANDE, disponible: 2 })),
    ).toBe('limitada');
    expect(
      nivelDisponibilidad(sembrar({ publico: CUPO_PUBLICO_GRANDE, disponible: 3 })),
    ).toBe('libre');
  });

  it('no divide por cero cuando el cupo público es cero', () => {
    expect(
      nivelDisponibilidad(
        sembrar({ publico: 0, disponible: 0 }),
        PORCENTAJE_AMPLIO,
      ),
    ).toBe('sin-cupo');
    expect(
      nivelDisponibilidad(
        sembrar({ publico: 0, disponible: 1 }),
        PORCENTAJE_AMPLIO,
      ),
    ).toBe('libre');
  });
});

describe('etiquetaNivel', () => {
  it('describe cada nivel con texto, no solo con color', () => {
    expect(etiquetaNivel('libre')).toBe('Con lugar');
    expect(etiquetaNivel('limitada')).toBe('Últimas plazas');
    expect(etiquetaNivel('sin-cupo')).toBe('Completo');
    expect(etiquetaNivel('sin-datos')).toBe('Sin datos');
  });
});

describe('cuposPublicosLibres', () => {
  const CUPO_MAXIMO = 10;
  const PLAZAS_EMERGENCIA = 1;
  const CUPO_PUBLICO = CUPO_MAXIMO - PLAZAS_EMERGENCIA;

  it('descuenta las plazas de emergencia del cupo máximo (RN-13)', () => {
    expect(
      cuposPublicosLibres({
        cupo_maximo: CUPO_MAXIMO,
        plazas_emergencia: PLAZAS_EMERGENCIA,
        ocupado: 0,
      }),
    ).toBe(CUPO_PUBLICO);
  });

  it('resta un cupo por cada plaza ocupada', () => {
    const base = {
      cupo_maximo: CUPO_MAXIMO,
      plazas_emergencia: PLAZAS_EMERGENCIA,
    };

    expect(cuposPublicosLibres({ ...base, ocupado: 3 })).toBe(CUPO_PUBLICO - 3);
    expect(cuposPublicosLibres({ ...base, ocupado: 4 })).toBe(CUPO_PUBLICO - 4);
  });

  it('no baja de cero cuando la ocupación ya superó el cupo público', () => {
    expect(
      cuposPublicosLibres({
        cupo_maximo: CUPO_MAXIMO,
        plazas_emergencia: PLAZAS_EMERGENCIA,
        ocupado: CUPO_MAXIMO + PLAZAS_EMERGENCIA,
      }),
    ).toBe(0);
  });
});
