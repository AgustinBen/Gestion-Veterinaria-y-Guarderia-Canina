import { useAuth } from '../../core/auth/contexto';
import { puedeAcceder, type Rol } from '../../core/auth/permisos';

export function puedeEscribirReservas(rol: Rol | null): boolean {
  return rol !== null && puedeAcceder(rol, 'nueva-reserva', 'escritura');
}

export function usePuedeEscribirReservas(): boolean {
  const { sesion } = useAuth();

  return puedeEscribirReservas(sesion?.rol ?? null);
}
