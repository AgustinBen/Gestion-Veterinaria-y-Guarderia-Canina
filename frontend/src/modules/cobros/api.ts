import { api, ApiError } from '../../core/api/client';
import { formatearDinero } from '../../core/formatos/dinero';

import type {
  AjusteNuevo,
  AjustePrecio,
  CargoDetalle,
  CuentaCliente,
  Deudor,
  MedioPago,
  OpcionesDeudores,
  OpcionesIdempotentes,
  Pago,
  PagoNuevo,
  PersonaBusqueda,
  ResumenDeuda,
} from './tipos';

type OpcionesLectura = {
  signal?: AbortSignal;
};

type OpcionesListadoPersonas = OpcionesLectura & {
  limite?: number;
  offset?: number;
};

function query(params: Record<string, string | number | boolean | undefined>): string {
  const busqueda = new URLSearchParams();

  for (const [clave, valor] of Object.entries(params)) {
    if (valor !== undefined && valor !== '') {
      busqueda.set(clave, String(valor));
    }
  }

  const texto = busqueda.toString();
  return texto ? `?${texto}` : '';
}

export function mensajeDeError(error: unknown): string {
  if (error instanceof Error && error.message.trim().length > 0) {
    return error.message;
  }

  return 'No pudimos completar la operación.';
}

/**
 * Si el 422 es por saldo insuficiente, la API informa el saldo restante en
 * centavos dentro del `detail`. Devuelve `null` para cualquier otro error.
 */
export function saldoRestanteDeError(error: unknown): number | null {
  if (!(error instanceof ApiError) || error.estado !== 422) {
    return null;
  }

  const detalle = typeof error.detalle === 'string' ? error.detalle : error.message;
  const coincidencia = /Saldo restante:\s*(\d+)/i.exec(detalle);

  if (!coincidencia) {
    return null;
  }

  const centavos = Number(coincidencia[1]);

  return Number.isSafeInteger(centavos) ? centavos : null;
}

export function mensajeDeSaldoRestante(centavos: number): string {
  return `El pago supera el saldo. Saldo restante: ${formatearDinero(centavos)}.`;
}

/**
 * Clave de idempotencia por apertura del formulario. Se reutiliza en los
 * reintentos por error de red para no registrar el pago dos veces.
 */
export function generarIdempotencyKey(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }

  return `idem-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

export function buscarPersonas(
  texto: string,
  opciones: OpcionesListadoPersonas = {},
): Promise<PersonaBusqueda[]> {
  return api.get<PersonaBusqueda[]>(
    `/personas${query({
      q: texto || undefined,
      limit: opciones.limite,
      offset: opciones.offset,
    })}`,
    { signal: opciones.signal },
  );
}

export function obtenerPersona(
  personaId: number,
  opciones: OpcionesLectura = {},
): Promise<PersonaBusqueda> {
  return api.get<PersonaBusqueda>(`/personas/${personaId}`, {
    signal: opciones.signal,
  });
}

export function listarMediosPago(opciones: OpcionesLectura = {}): Promise<MedioPago[]> {
  return api.get<MedioPago[]>('/medios-pago', { signal: opciones.signal });
}

export function obtenerCuentaCliente(
  personaId: number,
  opciones: OpcionesLectura = {},
): Promise<CuentaCliente> {
  return api.get<CuentaCliente>(`/personas/${personaId}/cuenta`, {
    signal: opciones.signal,
  });
}

export function obtenerResumenDeuda(
  personaId: number,
  opciones: OpcionesLectura = {},
): Promise<ResumenDeuda> {
  return api.get<ResumenDeuda>(`/personas/${personaId}/deuda`, {
    signal: opciones.signal,
  });
}

export function registrarPago(
  cargoId: number,
  datos: PagoNuevo,
  opciones: OpcionesIdempotentes,
): Promise<Pago> {
  return api.post<Pago>(`/cargos/${cargoId}/pagos`, datos, {
    idempotencyKey: opciones.idempotencyKey,
    signal: opciones.signal,
  });
}

export function ajustarPrecio(
  cargoId: number,
  datos: AjusteNuevo,
): Promise<AjustePrecio> {
  return api.post<AjustePrecio>(`/cargos/${cargoId}/ajustes`, datos);
}

export function listarDeudores(
  opciones: OpcionesDeudores = {},
): Promise<Deudor[]> {
  return api.get<Deudor[]>(
    `/deudores${query({
      orden: opciones.orden,
      solo_migracion: opciones.soloMigracion,
      limit: opciones.limite,
      offset: opciones.offset,
    })}`,
    { signal: opciones.signal },
  );
}

export function obtenerCargo(
  cargoId: number,
  opciones: OpcionesLectura = {},
): Promise<CargoDetalle> {
  return api.get<CargoDetalle>(`/cargos/${cargoId}`, {
    signal: opciones.signal,
  });
}
