import { leerSesion, notificarSesionExpirada } from '../auth/almacenSesion';

export type MetodoHttp = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

export type OpcionesSolicitud = {
  headers?: HeadersInit;
  signal?: AbortSignal;
};

export type OpcionesPost = OpcionesSolicitud & {
  /**
   * Marca la operación como crítica. El cliente genera una Idempotency-Key,
   * la mantiene en los reintentos por error de red y no la regenera.
   * Usar en pagos, reservas y habilitación de plaza de emergencia.
   */
  idempotente?: boolean;
  /** Clave provista por quien llama, por ejemplo al reintentar desde la UI. */
  idempotencyKey?: string;
  /** Reintentos extra ante error de red. Por defecto, 1. */
  reintentos?: number;
};

export type OpcionesCliente = {
  baseUrl?: string;
  getToken?: () => string | null;
  onNoAutorizado?: () => void;
  fetch?: typeof fetch;
  generarIdempotencyKey?: () => string;
  reintentosRed?: number;
};

export type TipoErrorApi = 'http' | 'red' | 'respuesta';

type OpcionesErrorApi = {
  tipo: TipoErrorApi;
  estado?: number;
  reintentable?: boolean;
  causa?: unknown;
};

export class ApiError extends Error {
  readonly tipo: TipoErrorApi;
  readonly estado: number | null;
  readonly reintentable: boolean;
  readonly causa?: unknown;

  constructor(mensaje: string, opciones: OpcionesErrorApi) {
    super(mensaje);
    this.name = 'ApiError';
    this.tipo = opciones.tipo;
    this.estado = opciones.estado ?? null;
    this.reintentable = opciones.reintentable ?? false;

    if (opciones.causa !== undefined) {
      this.causa = opciones.causa;
    }
  }
}

type OpcionesInternas = OpcionesPost & {
  cuerpo?: unknown;
};

function generarClaveIdempotencia(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }

  return `idem-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

async function leerDetalle(respuesta: Response): Promise<string | undefined> {
  try {
    const datos: unknown = await respuesta.json();

    if (typeof datos !== 'object' || datos === null) {
      return undefined;
    }

    const posible = datos as { detail?: unknown; mensaje?: unknown };
    const detalle = posible.detail ?? posible.mensaje;

    return typeof detalle === 'string' && detalle.trim().length > 0 ? detalle : undefined;
  } catch {
    return undefined;
  }
}

export class ClienteApi {
  private readonly baseUrl: string;
  private readonly getToken: () => string | null;
  private readonly onNoAutorizado: () => void;
  private readonly fetchImpl: typeof fetch;
  private readonly generarIdempotencyKey: () => string;
  private readonly reintentosRed: number;

  constructor(opciones: OpcionesCliente = {}) {
    const base = opciones.baseUrl ?? import.meta.env.VITE_API_URL?.trim() ?? '/api';

    this.baseUrl = (base || '/api').replace(/\/+$/, '');
    this.getToken = opciones.getToken ?? (() => leerSesion()?.token ?? null);
    this.onNoAutorizado = opciones.onNoAutorizado ?? notificarSesionExpirada;
    this.fetchImpl =
      opciones.fetch ?? ((...args: Parameters<typeof fetch>) => fetch(...args));
    this.generarIdempotencyKey = opciones.generarIdempotencyKey ?? generarClaveIdempotencia;
    this.reintentosRed = Math.max(0, opciones.reintentosRed ?? 1);
  }

  get<T>(ruta: string, opciones: OpcionesSolicitud = {}): Promise<T> {
    return this.solicitar<T>('GET', ruta, opciones);
  }

  post<T>(ruta: string, cuerpo: unknown, opciones: OpcionesPost = {}): Promise<T> {
    return this.solicitar<T>('POST', ruta, { ...opciones, cuerpo });
  }

  put<T>(ruta: string, cuerpo: unknown, opciones: OpcionesSolicitud = {}): Promise<T> {
    return this.solicitar<T>('PUT', ruta, { ...opciones, cuerpo });
  }

  patch<T>(ruta: string, cuerpo: unknown, opciones: OpcionesSolicitud = {}): Promise<T> {
    return this.solicitar<T>('PATCH', ruta, { ...opciones, cuerpo });
  }

  delete<T>(ruta: string, opciones: OpcionesSolicitud = {}): Promise<T> {
    return this.solicitar<T>('DELETE', ruta, opciones);
  }

  private async solicitar<T>(
    metodo: MetodoHttp,
    ruta: string,
    opciones: OpcionesInternas,
  ): Promise<T> {
    const clave =
      metodo === 'POST'
        ? opciones.idempotencyKey ??
          (opciones.idempotente ? this.generarIdempotencyKey() : undefined)
        : undefined;
    const maxIntentos =
      metodo === 'POST' && clave !== undefined
        ? 1 + Math.max(0, opciones.reintentos ?? this.reintentosRed)
        : 1;

    for (let intento = 1; intento <= maxIntentos; intento += 1) {
      try {
        return await this.ejecutar<T>(metodo, ruta, opciones, clave);
      } catch (fallo) {
        const puedeReintentar =
          fallo instanceof ApiError &&
          fallo.tipo === 'red' &&
          fallo.reintentable &&
          intento < maxIntentos;

        if (!puedeReintentar) {
          throw fallo;
        }
      }
    }

    throw new ApiError('No se pudo completar la solicitud.', { tipo: 'red' });
  }

  private async ejecutar<T>(
    metodo: MetodoHttp,
    ruta: string,
    opciones: OpcionesInternas,
    idempotencyKey: string | undefined,
  ): Promise<T> {
    const headers = new Headers(opciones.headers);
    const token = this.getToken();

    headers.set('Accept', 'application/json');

    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }

    if (opciones.cuerpo !== undefined) {
      headers.set('Content-Type', 'application/json');
    }

    if (idempotencyKey) {
      headers.set('Idempotency-Key', idempotencyKey);
    }

    let respuesta: Response;

    try {
      respuesta = await this.fetchImpl(this.url(ruta), {
        method: metodo,
        headers,
        body: opciones.cuerpo === undefined ? undefined : JSON.stringify(opciones.cuerpo),
        signal: opciones.signal,
      });
    } catch (fallo) {
      const abortado = fallo instanceof DOMException && fallo.name === 'AbortError';

      throw new ApiError(
        abortado ? 'La solicitud se canceló.' : 'No pudimos conectar con el servidor.',
        {
          tipo: 'red',
          reintentable: !abortado,
          causa: fallo,
        },
      );
    }

    if (respuesta.status === 401) {
      this.onNoAutorizado();
      throw new ApiError('Tu sesión venció. Volvé a iniciar sesión.', {
        tipo: 'http',
        estado: 401,
      });
    }

    if (respuesta.status === 403) {
      const detalle = await leerDetalle(respuesta);

      throw new ApiError(detalle ?? 'No tenés permiso para realizar esta acción.', {
        tipo: 'http',
        estado: 403,
      });
    }

    if (!respuesta.ok) {
      const detalle = await leerDetalle(respuesta);

      throw new ApiError(
        detalle ?? `Error ${respuesta.status} al comunicarse con el servidor.`,
        {
          tipo: 'http',
          estado: respuesta.status,
        },
      );
    }

    if (respuesta.status === 204) {
      return undefined as T;
    }

    const texto = await respuesta.text();

    if (!texto) {
      return undefined as T;
    }

    try {
      return JSON.parse(texto) as T;
    } catch {
      throw new ApiError('El servidor devolvió una respuesta inválida.', {
        tipo: 'respuesta',
        estado: respuesta.status,
      });
    }
  }

  private url(ruta: string): string {
    const rutaLimpia = ruta.startsWith('/') ? ruta : `/${ruta}`;
    return `${this.baseUrl}${rutaLimpia}`;
  }
}

export function crearCliente(opciones: OpcionesCliente = {}): ClienteApi {
  return new ClienteApi(opciones);
}

export const api = crearCliente();
