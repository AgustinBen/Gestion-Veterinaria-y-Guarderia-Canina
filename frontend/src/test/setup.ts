import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

/**
 * Node 25+ expone un `localStorage` global propio que devuelve `undefined`
 * cuando no se arranca con `--localstorage-file`, y tapa el que provee jsdom.
 * En ese caso instalamos un Storage en memoria para que los tests puedan
 * ejercitar el código que guarda la sesión.
 */
class AlmacenEnMemoria implements Storage {
  private readonly datos = new Map<string, string>();

  get length(): number {
    return this.datos.size;
  }

  clear(): void {
    this.datos.clear();
  }

  getItem(clave: string): string | null {
    return this.datos.get(clave) ?? null;
  }

  key(indice: number): string | null {
    return Array.from(this.datos.keys())[indice] ?? null;
  }

  removeItem(clave: string): void {
    this.datos.delete(clave);
  }

  setItem(clave: string, valor: string): void {
    this.datos.set(String(clave), String(valor));
  }
}

function asegurarAlmacenamiento(): Storage {
  const almacen = (window as { localStorage?: Storage }).localStorage;

  if (almacen) {
    return almacen;
  }

  const alternativo = new AlmacenEnMemoria();

  Object.defineProperty(window, 'localStorage', {
    configurable: true,
    enumerable: true,
    value: alternativo,
    writable: true,
  });

  if (globalThis !== window) {
    Object.defineProperty(globalThis, 'localStorage', {
      configurable: true,
      enumerable: true,
      value: alternativo,
      writable: true,
    });
  }

  return alternativo;
}

const almacenamiento = asegurarAlmacenamiento();

afterEach(() => {
  cleanup();
  almacenamiento.clear();
});
