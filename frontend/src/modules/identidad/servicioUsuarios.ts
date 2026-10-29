import { api } from '../../core/api/client';
import type { Rol } from '../../core/auth/permisos';

export type RolUsuarioCreable = Extract<Rol, 'PERSONAL' | 'VETERINARIO'>;

export type DatosUsuarioNuevo = {
  username: string;
  password: string;
  rol: RolUsuarioCreable;
};

type UsuarioCreado = {
  username: string;
  rol: RolUsuarioCreable;
};

/** Crea una cuenta mediante `POST /api/usuarios` con la sesión vigente. */
export function crearUsuario(datos: DatosUsuarioNuevo): Promise<UsuarioCreado> {
  return api.post<UsuarioCreado>('/usuarios', datos);
}
