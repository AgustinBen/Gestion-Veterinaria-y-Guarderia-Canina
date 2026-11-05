import { api } from '../../core/api/client';

import type {
  CategoriaEgreso,
  DetalleCliente,
  DeudasPanel,
  Egreso,
  EgresoNuevo,
  FiltrosPanel,
  GastoExterno,
  GastoExternoNuevo,
  IngresoHistorial,
  ListaGastos,
  OpcionesIdempotentes,
  ResumenPanel,
} from './tipos';

type OpcionesLectura = {
  signal?: AbortSignal;
};

function query(
  params: Record<string, string | number | boolean | undefined | null>,
): string {
  const busqueda = new URLSearchParams();

  for (const [clave, valor] of Object.entries(params)) {
    if (valor !== undefined && valor !== null && valor !== '') {
      busqueda.set(clave, String(valor));
    }
  }

  const texto = busqueda.toString();
  return texto ? `?${texto}` : '';
}

function filtrosQuery(filtros: FiltrosPanel): Record<string, string | undefined> {
  return {
    desde: filtros.desde || undefined,
    hasta: filtros.hasta || undefined,
  };
}

export function mensajeDeError(error: unknown): string {
  if (error instanceof Error && error.message.trim().length > 0) {
    return error.message;
  }

  return 'No pudimos completar la operación.';
}

export function generarIdempotencyKey(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }

  return `idem-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

export function listarResumen(
  filtros: FiltrosPanel,
  opciones: OpcionesLectura = {},
): Promise<ResumenPanel> {
  return api.get<ResumenPanel>(`/panel/resumen${query(filtrosQuery(filtros))}`, {
    signal: opciones.signal,
  });
}

export function listarIngresos(
  filtros: FiltrosPanel,
  opciones: OpcionesLectura = {},
): Promise<IngresoHistorial[]> {
  return api.get<IngresoHistorial[]>(
    `/panel/ingresos${query(filtrosQuery(filtros))}`,
    { signal: opciones.signal },
  );
}

export function obtenerDeudas(
  opciones: OpcionesLectura = {},
): Promise<DeudasPanel> {
  return api.get<DeudasPanel>('/panel/deudas', { signal: opciones.signal });
}

export function obtenerDetalleCliente(
  personaId: number,
  opciones: OpcionesLectura = {},
): Promise<DetalleCliente> {
  return api.get<DetalleCliente>(`/panel/clientes/${personaId}/servicios`, {
    signal: opciones.signal,
  });
}

export function listarCategoriasEgreso(
  opciones: OpcionesLectura = {},
): Promise<CategoriaEgreso[]> {
  return api.get<CategoriaEgreso[]>('/categorias-egreso', {
    signal: opciones.signal,
  });
}

export function crearCategoriaEgreso(nombre: string): Promise<CategoriaEgreso> {
  return api.post<CategoriaEgreso>('/categorias-egreso', { nombre });
}

export function actualizarCategoriaEgreso(
  categoriaId: number,
  activa: boolean,
): Promise<CategoriaEgreso> {
  return api.patch<CategoriaEgreso>(`/categorias-egreso/${categoriaId}`, {
    activa,
  });
}

export function listarEgresos(
  filtros: { desde: string; hasta: string; categoriaId?: number | null },
  opciones: OpcionesLectura = {},
): Promise<Egreso[]> {
  return api.get<Egreso[]>(
    `/egresos${query({
      desde: filtros.desde || undefined,
      hasta: filtros.hasta || undefined,
      categoria_id: filtros.categoriaId ?? undefined,
    })}`,
    { signal: opciones.signal },
  );
}

export function crearEgreso(
  datos: EgresoNuevo,
  opciones: OpcionesIdempotentes,
): Promise<Egreso> {
  return api.post<Egreso>('/egresos', datos, {
    idempotencyKey: opciones.idempotencyKey,
    signal: opciones.signal,
  });
}

export function anularEgreso(
  egresoId: number,
  motivo: string,
): Promise<Egreso> {
  return api.post<Egreso>(`/egresos/${egresoId}/anular`, { motivo }, {
    idempotente: true,
  });
}

export function listarGastosExternos(
  filtros: { desde: string; hasta: string },
  opciones: OpcionesLectura = {},
): Promise<ListaGastos> {
  return api.get<ListaGastos>(
    `/gastos-externos${query({
      desde: filtros.desde || undefined,
      hasta: filtros.hasta || undefined,
      limit: 100,
    })}`,
    { signal: opciones.signal },
  );
}

export function crearGastoExterno(
  datos: GastoExternoNuevo,
  opciones: OpcionesIdempotentes,
): Promise<GastoExterno> {
  return api.post<GastoExterno>('/gastos-externos', datos, {
    idempotencyKey: opciones.idempotencyKey,
    signal: opciones.signal,
  });
}

export function anularGastoExterno(
  gastoId: number,
  motivo: string,
): Promise<GastoExterno> {
  return api.post<GastoExterno>(
    `/gastos-externos/${gastoId}/anular`,
    { motivo },
    { idempotente: true },
  );
}
