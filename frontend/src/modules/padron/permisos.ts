import { useAuth } from '../../core/auth/contexto';
import { puedeAcceder } from '../../core/auth/permisos';

/**
 * Nivel de escritura del padrón según la matriz de permisos de T-09.
 * Las pantallas nunca comparan el rol a mano.
 */
export function usePuedeEscribirPadron(): boolean {
  const { sesion } = useAuth();

  return sesion ? puedeAcceder(sesion.rol, 'padron', 'escritura') : false;
}
