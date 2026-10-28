import { api } from '../api/client';
import { esRol, type Rol } from './permisos';

export type CredencialesApi = {
  username: string;
  password: string;
};

export type SesionApi = {
  token: string;
  rol: Rol;
};

export type UsuarioAutenticado = {
  id: number;
  username: string;
  rol: Rol;
  empleado_id: number | null;
};

type RespuestaLogin = {
  access_token: string;
  token_type: string;
  rol: string;
};

function validarRol(rol: unknown): Rol {
  if (!esRol(rol)) {
    throw new Error('El servidor devolvió un rol inválido.');
  }

  return rol;
}

/** Autentica contra `POST /api/auth/login`. */
export async function iniciarSesionApi(credenciales: CredencialesApi): Promise<SesionApi> {
  const respuesta = await api.post<RespuestaLogin>('/auth/login', credenciales, {
    // Un 401 acá significa credenciales incorrectas, no sesión vencida.
    sinSesion: true,
  });

  return {
    token: respuesta.access_token,
    rol: validarRol(respuesta.rol),
  };
}

/** Devuelve el usuario dueño del token y su rol vigente. */
export async function solicitarUsuarioActual(): Promise<UsuarioAutenticado> {
  const usuario = await api.get<UsuarioAutenticado>('/auth/me');

  return { ...usuario, rol: validarRol(usuario.rol) };
}

/**
 * Avisa al backend que la sesión termina. Hoy el servidor no revoca el token,
 * así que la limpieza real la hace el cliente al borrar la sesión local.
 */
export async function cerrarSesionApi(token: string): Promise<void> {
  await api.post<void>('/auth/logout', undefined, {
    headers: { Authorization: `Bearer ${token}` },
    sinNotificarNoAutorizado: true,
  });
}
