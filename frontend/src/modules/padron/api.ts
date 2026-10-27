import { api, ApiError } from '../../core/api/client';

import type {
  CoincidenciaDuplicado,
  ErrorDuplicado,
  Especie,
  PacienteActualizar,
  PacienteDetalle,
  PacienteNuevo,
  PacienteResumen,
  PersonaActualizar,
  PersonaDetalle,
  PersonaNueva,
  PersonaResumen,
  Raza,
  RazaNueva,
  Tamanio,
  TitularVigente,
} from './tipos';

type OpcionesLectura = {
  signal?: AbortSignal;
};

type OpcionesListado = OpcionesLectura & {
  limite?: number;
  offset?: number;
};

function query(params: Record<string, string | number | undefined>): string {
  const busqueda = new URLSearchParams();

  for (const [clave, valor] of Object.entries(params)) {
    if (valor !== undefined && valor !== '') {
      busqueda.set(clave, String(valor));
    }
  }

  const texto = busqueda.toString();
  return texto ? `?${texto}` : '';
}

function esRegistro(valor: unknown): valor is Record<string, unknown> {
  return typeof valor === 'object' && valor !== null;
}

function esCoincidencia(valor: unknown): valor is CoincidenciaDuplicado {
  return (
    esRegistro(valor) &&
    esRegistro(valor.persona) &&
    typeof valor.motivo === 'string' &&
    Array.isArray(valor.mascotas)
  );
}

/**
 * Interpreta el `detail` de un 409 del padrón. Devuelve `null` si el error no
 * es de duplicados, para que la pantalla muestre el mensaje genérico.
 */
export function leerErrorDuplicado(error: unknown): ErrorDuplicado | null {
  if (!(error instanceof ApiError) || !esRegistro(error.detalle)) {
    return null;
  }

  const codigo = error.detalle.codigo;

  if (codigo === 'DNI_DUPLICADO' && esRegistro(error.detalle.persona)) {
    return {
      codigo,
      persona: error.detalle.persona as PersonaResumen,
    };
  }

  if (codigo === 'POSIBLE_DUPLICADO' && Array.isArray(error.detalle.coincidencias)) {
    return {
      codigo,
      coincidencias: error.detalle.coincidencias.filter(esCoincidencia),
    };
  }

  return null;
}

export function mensajeDeError(error: unknown): string {
  if (error instanceof Error && error.message.trim().length > 0) {
    return error.message;
  }

  return 'No pudimos completar la operación.';
}

export function buscarPersonas(
  texto: string,
  opciones: OpcionesLectura = {},
): Promise<PersonaResumen[]> {
  return api.get<PersonaResumen[]>(`/personas${query({ q: texto })}`, {
    signal: opciones.signal,
  });
}

/** Lista personas sin filtro. El backend ordena por apellido y aplica el límite. */
export function listarPersonas(
  opciones: OpcionesListado = {},
): Promise<PersonaResumen[]> {
  return api.get<PersonaResumen[]>(
    `/personas${query({ limit: opciones.limite, offset: opciones.offset })}`,
    { signal: opciones.signal },
  );
}

export function listarPacientes(
  opciones: OpcionesListado = {},
): Promise<PacienteResumen[]> {
  return api.get<PacienteResumen[]>(
    `/pacientes${query({ limit: opciones.limite, offset: opciones.offset })}`,
    { signal: opciones.signal },
  );
}

export function obtenerPersona(
  personaId: number,
  opciones: OpcionesLectura = {},
): Promise<PersonaDetalle> {
  return api.get<PersonaDetalle>(`/personas/${personaId}`, {
    signal: opciones.signal,
  });
}

export function crearPersona(datos: PersonaNueva): Promise<PersonaDetalle> {
  return api.post<PersonaDetalle>('/personas', datos);
}

export function actualizarPersona(
  personaId: number,
  datos: PersonaActualizar,
): Promise<PersonaDetalle> {
  return api.patch<PersonaDetalle>(`/personas/${personaId}`, datos);
}

export function buscarPacientes(
  texto: string,
  opciones: OpcionesLectura = {},
): Promise<PacienteResumen[]> {
  return api.get<PacienteResumen[]>(`/pacientes${query({ q: texto })}`, {
    signal: opciones.signal,
  });
}

export function obtenerPaciente(
  pacienteId: number,
  opciones: OpcionesLectura = {},
): Promise<PacienteDetalle> {
  return api.get<PacienteDetalle>(`/pacientes/${pacienteId}`, {
    signal: opciones.signal,
  });
}

export function crearPaciente(datos: PacienteNuevo): Promise<PacienteDetalle> {
  return api.post<PacienteDetalle>('/pacientes', datos);
}

export function actualizarPaciente(
  pacienteId: number,
  datos: PacienteActualizar,
): Promise<PacienteDetalle> {
  return api.patch<PacienteDetalle>(`/pacientes/${pacienteId}`, datos);
}

export function obtenerTitulares(
  pacienteId: number,
  opciones: OpcionesLectura = {},
): Promise<TitularVigente[]> {
  return api.get<TitularVigente[]>(`/pacientes/${pacienteId}/titulares`, {
    signal: opciones.signal,
  });
}

export function listarEspecies(opciones: OpcionesLectura = {}): Promise<Especie[]> {
  return api.get<Especie[]>('/especies', { signal: opciones.signal });
}

export function listarRazas(
  especieId?: number,
  opciones: OpcionesLectura = {},
): Promise<Raza[]> {
  return api.get<Raza[]>(`/razas${query({ especie_id: especieId })}`, {
    signal: opciones.signal,
  });
}

export function listarTamanios(opciones: OpcionesLectura = {}): Promise<Tamanio[]> {
  return api.get<Tamanio[]>('/tamanios', { signal: opciones.signal });
}

export function crearRaza(datos: RazaNueva): Promise<Raza> {
  return api.post<Raza>('/razas', datos);
}
