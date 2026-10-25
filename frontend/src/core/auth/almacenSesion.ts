import { esRol, type Rol } from './permisos';

export type Sesion = {
  token: string;
  rol: Rol;
  usuario: string;
};

const CLAVE_SESION = 'huellitas.sesion';

export const EVENTO_SESION_EXPIRADA = 'huellitas:sesion-expirada';

function esSesion(valor: unknown): valor is Sesion {
  if (typeof valor !== 'object' || valor === null) {
    return false;
  }

  const posible = valor as Record<string, unknown>;

  return (
    typeof posible.token === 'string' &&
    posible.token.length > 0 &&
    esRol(posible.rol) &&
    typeof posible.usuario === 'string'
  );
}

export function leerSesion(): Sesion | null {
  try {
    const guardada = window.localStorage.getItem(CLAVE_SESION);

    if (!guardada) {
      return null;
    }

    const sesion: unknown = JSON.parse(guardada);

    if (esSesion(sesion)) {
      return sesion;
    }

    borrarSesion();
    return null;
  } catch {
    borrarSesion();
    return null;
  }
}

export function guardarSesion(sesion: Sesion): void {
  window.localStorage.setItem(CLAVE_SESION, JSON.stringify(sesion));
}

export function borrarSesion(): void {
  try {
    window.localStorage.removeItem(CLAVE_SESION);
  } catch {
    // Si el navegador bloquea el almacenamiento no hay nada que limpiar.
  }
}

export function notificarSesionExpirada(): void {
  borrarSesion();
  window.dispatchEvent(new Event(EVENTO_SESION_EXPIRADA));
}
