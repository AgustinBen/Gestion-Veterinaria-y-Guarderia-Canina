import { api, ApiError } from '../../core/api/client';
import { leerSesion } from '../../core/auth/almacenSesion';

import type {
  AdjuntoResumen,
  AgendaDia,
  AtencionCrear,
  AtencionDetalle,
  AtencionResumen,
  CategoriaClinica,
  ErrorAgenda,
  EstudioCrear,
  EstudioResumen,
  EventoExterno,
  HorarioAtencion,
  LibretaVacunasItem,
  MedioEventoExterno,
  Turno,
  TurnoAtendido,
  TurnoCrear,
  TurnoReprogramar,
  TipoAtencion,
  EstadoTurno,
} from './tipos';
import type { PacienteResumen } from '../padron/tipos';

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

/** `detail` puede ser texto o `{ codigo, mensaje }` en los errores de agenda. */
export function mensajeDeError(error: unknown): string {
  if (error instanceof ApiError && esRegistro(error.detalle)) {
    const mensaje = error.detalle.mensaje;

    if (typeof mensaje === 'string' && mensaje.trim().length > 0) {
      return mensaje;
    }
  }

  if (error instanceof Error && error.message.trim().length > 0) {
    return error.message;
  }

  return 'No pudimos completar la operación.';
}

export function leerErrorAgenda(error: unknown): ErrorAgenda | null {
  if (!(error instanceof ApiError) || !esRegistro(error.detalle)) {
    return null;
  }

  const { codigo, mensaje } = error.detalle;

  if (typeof codigo !== 'string' || typeof mensaje !== 'string') {
    return null;
  }

  return { codigo, mensaje };
}

/* ------------------------------- Historia ------------------------------- */

export function crearAtencion(
  pacienteId: number,
  datos: AtencionCrear,
): Promise<AtencionDetalle> {
  return api.post<AtencionDetalle>(`/pacientes/${pacienteId}/atenciones`, datos);
}

export function listarAtenciones(
  pacienteId: number,
  opciones: OpcionesListado & {
    tipo?: TipoAtencion;
    desde?: string;
    hasta?: string;
  } = {},
): Promise<AtencionResumen[]> {
  return api.get<AtencionResumen[]>(
    `/pacientes/${pacienteId}/atenciones${query({
      tipo: opciones.tipo,
      desde: opciones.desde,
      hasta: opciones.hasta,
      limit: opciones.limite,
      offset: opciones.offset,
    })}`,
    { signal: opciones.signal },
  );
}

export function listarPacientesPorAtencion(
  tipo: CategoriaClinica,
  opciones: OpcionesLectura = {},
): Promise<PacienteResumen[]> {
  return api.get<PacienteResumen[]>(
    `/clinica/pacientes-por-atencion${query({ tipo })}`,
    { signal: opciones.signal },
  );
}

export function listarIdsVeterinarios(
  opciones: OpcionesLectura = {},
): Promise<number[]> {
  return api.get<number[]>('/clinica/veterinarios', {
    signal: opciones.signal,
  });
}

export function obtenerAtencion(
  atencionId: number,
  opciones: OpcionesLectura = {},
): Promise<AtencionDetalle> {
  return api.get<AtencionDetalle>(`/atenciones/${atencionId}`, {
    signal: opciones.signal,
  });
}

export function rectificarAtencion(
  atencionId: number,
  datos: AtencionCrear,
): Promise<AtencionDetalle> {
  return api.post<AtencionDetalle>(`/atenciones/${atencionId}/rectificar`, datos);
}

export function obtenerLibreta(
  pacienteId: number,
  opciones: OpcionesLectura = {},
): Promise<LibretaVacunasItem[]> {
  return api.get<LibretaVacunasItem[]>(
    `/pacientes/${pacienteId}/libreta-vacunas`,
    { signal: opciones.signal },
  );
}

/* -------------------------------- Estudios ------------------------------- */

export function crearEstudio(
  pacienteId: number,
  datos: EstudioCrear,
): Promise<EstudioResumen> {
  return api.post<EstudioResumen>(`/pacientes/${pacienteId}/estudios`, datos);
}

export function listarEstudios(
  pacienteId: number,
  opciones: OpcionesLectura = {},
): Promise<EstudioResumen[]> {
  return api.get<EstudioResumen[]>(`/pacientes/${pacienteId}/estudios`, {
    signal: opciones.signal,
  });
}

function urlApi(ruta: string): string {
  const base = import.meta.env.VITE_API_URL?.trim() || '/api';

  return `${base.replace(/\/+$/, '')}${ruta.startsWith('/') ? ruta : `/${ruta}`}`;
}

function mensajeDeCuerpo(texto: string): string | undefined {
  try {
    const datos: unknown = JSON.parse(texto);

    if (typeof datos === 'string') {
      return datos;
    }

    if (esRegistro(datos)) {
      if (typeof datos.detail === 'string') {
        return datos.detail;
      }

      if (esRegistro(datos.detail) && typeof datos.detail.mensaje === 'string') {
        return datos.detail.mensaje;
      }
    }
  } catch {
    return undefined;
  }

  return undefined;
}

/**
 * Sube un adjunto con `XMLHttpRequest` para informar el progreso. El cliente
 * JSON no sirve porque fuerza `Content-Type: application/json`.
 */
export function subirAdjunto(
  estudioId: number,
  archivo: File,
  opciones: {
    onProgreso?: (fraccion: number) => void;
    signal?: AbortSignal;
  } = {},
): Promise<AdjuntoResumen> {
  return new Promise((resolver, rechazar) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', urlApi(`/estudios/${estudioId}/adjuntos`));
    xhr.setRequestHeader('Accept', 'application/json');

    const token = leerSesion()?.token;

    if (token) {
      xhr.setRequestHeader('Authorization', `Bearer ${token}`);
    }

    if (opciones.signal?.aborted) {
      rechazar(new ApiError('La subida se canceló.', { tipo: 'red' }));
      return;
    }

    const abortar = () => xhr.abort();
    opciones.signal?.addEventListener('abort', abortar);

    const finalizar = () => {
      opciones.signal?.removeEventListener('abort', abortar);
    };

    xhr.upload.onprogress = (evento) => {
      if (evento.lengthComputable && evento.total > 0) {
        opciones.onProgreso?.(evento.loaded / evento.total);
      }
    };

    xhr.onload = () => {
      finalizar();

      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolver(JSON.parse(xhr.responseText) as AdjuntoResumen);
        } catch {
          rechazar(
            new ApiError('El servidor devolvió una respuesta inválida.', {
              tipo: 'respuesta',
              estado: xhr.status,
            }),
          );
        }
        return;
      }

      rechazar(
        new ApiError(
          mensajeDeCuerpo(xhr.responseText) ??
            `Error ${xhr.status} al subir el archivo.`,
          { tipo: 'http', estado: xhr.status },
        ),
      );
    };

    xhr.onerror = () => {
      finalizar();
      rechazar(
        new ApiError('No pudimos conectar con el servidor.', {
          tipo: 'red',
          reintentable: true,
        }),
      );
    };

    xhr.onabort = () => {
      finalizar();
      rechazar(new ApiError('La subida se canceló.', { tipo: 'red' }));
    };

    const formulario = new FormData();
    formulario.append('archivo', archivo);
    xhr.send(formulario);
  });
}

export async function descargarAdjunto(adjuntoId: number): Promise<Blob> {
  const token = leerSesion()?.token;
  const headers = new Headers();

  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const respuesta = await fetch(urlApi(`/adjuntos/${adjuntoId}/archivo`), {
    headers,
  });

  if (!respuesta.ok) {
    throw new ApiError(`Error ${respuesta.status} al descargar el archivo.`, {
      tipo: 'http',
      estado: respuesta.status,
    });
  }

  return respuesta.blob();
}

export function eliminarAdjunto(adjuntoId: number): Promise<void> {
  return api.delete<void>(`/adjuntos/${adjuntoId}`);
}

/* -------------------------------- Horarios ------------------------------- */

export function obtenerHorarios(
  opciones: OpcionesLectura = {},
): Promise<HorarioAtencion[]> {
  return api.get<HorarioAtencion[]>('/clinica/horarios', {
    signal: opciones.signal,
  });
}

export function actualizarHorarios(
  horarios: Omit<HorarioAtencion, 'id'>[],
): Promise<HorarioAtencion[]> {
  return api.put<HorarioAtencion[]>('/clinica/horarios', horarios);
}

/* --------------------------------- Turnos -------------------------------- */

export function crearTurno(datos: TurnoCrear): Promise<Turno> {
  return api.post<Turno>('/turnos', datos);
}

export function listarTurnos(
  opciones: OpcionesLectura & {
    desde?: string;
    hasta?: string;
    veterinarioId?: number;
    pacienteId?: number;
    estado?: EstadoTurno;
  } = {},
): Promise<Turno[]> {
  return api.get<Turno[]>(
    `/turnos${query({
      desde: opciones.desde,
      hasta: opciones.hasta,
      veterinario_id: opciones.veterinarioId,
      paciente_id: opciones.pacienteId,
      estado: opciones.estado,
    })}`,
    { signal: opciones.signal },
  );
}

export function obtenerTurno(
  turnoId: number,
  opciones: OpcionesLectura = {},
): Promise<Turno> {
  return api.get<Turno>(`/turnos/${turnoId}`, { signal: opciones.signal });
}

export function reprogramarTurno(
  turnoId: number,
  datos: TurnoReprogramar,
): Promise<Turno> {
  return api.patch<Turno>(`/turnos/${turnoId}`, datos);
}

export function cancelarTurno(turnoId: number, motivo: string): Promise<Turno> {
  return api.post<Turno>(`/turnos/${turnoId}/cancelar`, { motivo });
}

export function marcarTurnoAusente(turnoId: number): Promise<Turno> {
  return api.post<Turno>(`/turnos/${turnoId}/ausente`, {});
}

export function marcarTurnoAtendido(
  turnoId: number,
  atencionId?: number,
): Promise<TurnoAtendido> {
  return api.post<TurnoAtendido>(`/turnos/${turnoId}/atendido`, {
    atencion_id: atencionId ?? null,
  });
}

export function listarEventosExterno(
  turnoId: number,
  opciones: OpcionesLectura = {},
): Promise<EventoExterno[]> {
  return api.get<EventoExterno[]>(`/turnos/${turnoId}/externo`, {
    signal: opciones.signal,
  });
}

export function contactarExterno(
  turnoId: number,
  datos: { medio: MedioEventoExterno; nota?: string | null },
): Promise<EventoExterno> {
  return api.post<EventoExterno>(`/turnos/${turnoId}/externo/contactado`, datos);
}

export function confirmarExterno(
  turnoId: number,
  costoAcordadoCentavos: number,
): Promise<EventoExterno> {
  return api.post<EventoExterno>(`/turnos/${turnoId}/externo/confirmar`, {
    costo_acordado_centavos: costoAcordadoCentavos,
  });
}

export function rechazarExterno(
  turnoId: number,
  motivo: string,
): Promise<EventoExterno> {
  return api.post<EventoExterno>(`/turnos/${turnoId}/externo/rechazar`, {
    motivo,
  });
}

export function reemplazarExterno(
  turnoId: number,
  externoEmpleadoId: number,
): Promise<EventoExterno> {
  return api.post<EventoExterno>(`/turnos/${turnoId}/externo/reemplazar`, {
    externo_empleado_id: externoEmpleadoId,
  });
}

/* --------------------------------- Agenda -------------------------------- */

export function obtenerAgenda(
  opciones: OpcionesLectura & {
    desde: string;
    hasta: string;
    veterinarioId?: number;
  },
): Promise<AgendaDia[]> {
  return api.get<AgendaDia[]>(
    `/clinica/agenda${query({
      desde: opciones.desde,
      hasta: opciones.hasta,
      veterinario_id: opciones.veterinarioId,
    })}`,
    { signal: opciones.signal },
  );
}
