import { api, ApiError } from '../../core/api/client';

import type {
  Disponibilidad,
  ErrorReserva,
  Franja,
  FranjaSinLugar,
  OcupacionExistente,
  OpcionesIdempotentes,
  OpcionesLectura,
  Reserva,
  ReservaCrear,
  ReservaSenaCrear,
} from './tipos';

function esRegistro(valor: unknown): valor is Record<string, unknown> {
  return typeof valor === 'object' && valor !== null;
}

function esFranja(valor: unknown): valor is Franja {
  return valor === 'DIA' || valor === 'NOCHE';
}

function esFranjaSinLugar(valor: unknown): valor is FranjaSinLugar {
  return (
    esRegistro(valor) &&
    typeof valor.fecha === 'string' &&
    esFranja(valor.franja) &&
    typeof valor.necesita === 'number' &&
    typeof valor.disponible === 'number'
  );
}

function esOcupacionExistente(valor: unknown): valor is OcupacionExistente {
  return (
    esRegistro(valor) &&
    typeof valor.paciente_id === 'number' &&
    typeof valor.fecha === 'string' &&
    esFranja(valor.franja)
  );
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

export function leerErrorReserva(error: unknown): ErrorReserva | null {
  if (!(error instanceof ApiError) || !esRegistro(error.detalle)) {
    return null;
  }

  const codigo = error.detalle.codigo;

  if (codigo !== 'SIN_CUPO' && codigo !== 'YA_RESERVADO') {
    return null;
  }

  const franjasSinLugar = Array.isArray(error.detalle.franjas_sin_lugar)
    ? error.detalle.franjas_sin_lugar.filter(esFranjaSinLugar)
    : [];
  const ocupacionesExistentes = Array.isArray(error.detalle.ocupaciones_existentes)
    ? error.detalle.ocupaciones_existentes.filter(esOcupacionExistente)
    : [];

  return {
    codigo,
    franjas_sin_lugar: franjasSinLugar,
    ocupaciones_existentes: ocupacionesExistentes,
  };
}

export function listarCalendario(
  desde: string,
  hasta: string,
  opciones: OpcionesLectura = {},
): Promise<Disponibilidad[]> {
  const params = new URLSearchParams({ desde, hasta });

  return api.get<Disponibilidad[]>(`/guarderia/calendario?${params.toString()}`, {
    signal: opciones.signal,
  });
}

export function crearReserva(
  datos: ReservaCrear,
  opciones: OpcionesIdempotentes,
): Promise<Reserva> {
  return api.post<Reserva>('/guarderia/reservas', datos, {
    idempotencyKey: opciones.idempotencyKey,
    signal: opciones.signal,
  });
}

export function registrarSena(
  reservaId: number,
  datos: ReservaSenaCrear,
  opciones: OpcionesIdempotentes,
): Promise<Reserva> {
  return api.post<Reserva>(`/guarderia/reservas/${reservaId}/sena`, datos, {
    idempotencyKey: opciones.idempotencyKey,
    signal: opciones.signal,
  });
}

export function obtenerReserva(
  reservaId: number,
  opciones: OpcionesLectura = {},
): Promise<Reserva> {
  return api.get<Reserva>(`/guarderia/reservas/${reservaId}`, {
    signal: opciones.signal,
  });
}
