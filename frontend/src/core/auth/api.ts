import { api } from '../api/client';
import type { Rol } from './permisos';

export type RespuestaLogin = {
  access_token: string;
  token_type: string;
  rol: Rol;
};

export function iniciarSesionApi(usuario: string, password: string) {
  return api.post<RespuestaLogin>(
    '/auth/login',
    { username: usuario, password },
    { sinSesion: true },
  );
}