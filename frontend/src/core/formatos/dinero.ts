/**
 * Formato y lectura de dinero en pesos argentinos.
 *
 * Todo el dinero del frontend viaja en centavos enteros. Estas funciones no
 * usan `parseFloat` ni divisiones con coma flotante: separan la parte entera de
 * los centavos y operan con enteros.
 */

const SIMBOLO = '$';

function agruparMiles(entero: string): string {
  return entero.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
}

/** Monto sin símbolo: 123456 → "1.234,56". */
export function formatearMonto(centavos: number): string {
  if (!Number.isSafeInteger(centavos)) {
    throw new Error('El monto debe ser un número entero de centavos.');
  }

  const negativo = centavos < 0;
  const absoluto = Math.abs(centavos);
  const enteros = Math.floor(absoluto / 100);
  const decimales = String(absoluto % 100).padStart(2, '0');
  const texto = `${agruparMiles(String(enteros))},${decimales}`;

  return negativo ? `-${texto}` : texto;
}

/** Dinero con símbolo: 123456 → "$1.234,56". */
export function formatearDinero(centavos: number): string {
  const monto = formatearMonto(centavos);

  return monto.startsWith('-') ? `-${SIMBOLO}${monto.slice(1)}` : `${SIMBOLO}${monto}`;
}

/**
 * Convierte lo que escribe la persona a centavos enteros.
 *
 * Acepta "10.000" (1.000.000 centavos), "10.000,50" (1.000.050) y "1,5" (150).
 * El punto es separador de miles y la coma separador decimal. Lanza `Error`
 * ante texto inválido, negativo o con más de dos decimales.
 */
export function parsearDinero(texto: string): number {
  const limpio = texto
    .trim()
    .replace(/^\$\s*/, '')
    .replace(/\s+/g, '');

  if (!limpio) {
    throw new Error('Ingresá un monto.');
  }

  const conMiles = /^\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?$/;
  const sinMiles = /^\d+(?:,\d{1,2})?$/;

  if (!conMiles.test(limpio) && !sinMiles.test(limpio)) {
    throw new Error('Monto inválido. Usá solo números, por ejemplo 10.000 o 10.000,50.');
  }

  const [parteEntera = '', parteDecimal = ''] = limpio.split(',');
  const enteros = Number(parteEntera.replace(/\./g, ''));
  const decimales = Number(parteDecimal.padEnd(2, '0'));
  const centavos = enteros * 100 + decimales;

  if (!Number.isSafeInteger(centavos) || centavos <= 0) {
    throw new Error('El monto debe ser mayor a cero.');
  }

  return centavos;
}
