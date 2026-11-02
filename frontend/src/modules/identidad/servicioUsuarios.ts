import { api } from '../../core/api/client';
import type { Rol } from '../../core/auth/permisos';

export type RolUsuarioCreable = Extract<Rol, 'PERSONAL' | 'VETERINARIO'>;

/** Datos del empleado que se da de alta junto con la cuenta (RN-01). */
export type DatosEmpleadoCuenta = {
  nombre: string;
  apellido: string;
  dni: string;
  telefono: string;
  especialidad?: string;
  confirmar_duplicado?: boolean;
  persona_coincidente_id?: number;
};

export type DatosUsuarioNuevo = {
  username: string;
  password: string;
  rol: RolUsuarioCreable;
  empleado: DatosEmpleadoCuenta;
};

type UsuarioCreado = {
  username: string;
  rol: RolUsuarioCreable;
  empleado_id: number | null;
};

/**
 * Crea una cuenta mediante `POST /api/usuarios` con la sesión vigente. El
 * backend da de alta el empleado y lo vincula a la cuenta.
 */
export function crearUsuario(datos: DatosUsuarioNuevo): Promise<UsuarioCreado> {
  return api.post<UsuarioCreado>('/usuarios', datos);
}
