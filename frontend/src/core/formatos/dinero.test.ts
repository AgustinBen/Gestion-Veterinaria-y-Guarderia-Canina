import { describe, expect, it } from 'vitest';

import { formatearDinero, formatearMonto, parsearDinero } from './dinero';

describe('formatearDinero', () => {
  it('formatea centavos como pesos con separador de miles y coma decimal', () => {
    expect(formatearDinero(123456)).toBe('$1.234,56');
  });

  it('mantiene los centavos con dos dígitos', () => {
    expect(formatearDinero(1000000)).toBe('$10.000,00');
    expect(formatearDinero(5)).toBe('$0,05');
  });

  it('formatea negativos sin romper el símbolo', () => {
    expect(formatearDinero(-123456)).toBe('-$1.234,56');
  });

  it('expone el monto sin símbolo para los campos editables', () => {
    expect(formatearMonto(123456)).toBe('1.234,56');
  });
});

describe('parsearDinero', () => {
  it('convierte "10.000" a un millón de centavos', () => {
    expect(parsearDinero('10.000')).toBe(1000000);
  });

  it('convierte "10.000,50" a centavos exactos', () => {
    expect(parsearDinero('10.000,50')).toBe(1000050);
  });

  it('convierte "1,5" a 150 centavos', () => {
    expect(parsearDinero('1,5')).toBe(150);
  });

  it('acepta el símbolo y espacios', () => {
    expect(parsearDinero('$ 1.234,56')).toBe(123456);
  });

  it('no pasa por coma flotante: 0,1 + 0,2 da 30 centavos exactos', () => {
    const total = parsearDinero('0,1') + parsearDinero('0,2');

    expect(total).toBe(30);
    expect(Number.isInteger(total)).toBe(true);
  });

  it.each(['', '   ', 'abc', '-5', '-1.000', '10,999', '1.5', '1,2,3', '$'])(
    'rechaza el texto inválido o negativo %j',
    (texto) => {
      expect(() => parsearDinero(texto)).toThrow();
    },
  );

  it('rechaza cero porque no es un monto cobrable', () => {
    expect(() => parsearDinero('0')).toThrow();
  });
});
