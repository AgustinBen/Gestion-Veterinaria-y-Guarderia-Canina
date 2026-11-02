import { useAuth } from '../../core/auth/contexto';
import { puedeAcceder, type Rol } from '../../core/auth/permisos';

/** La escritura de la historia clínica es de VETERINARIO y DUENIO (RN-40). */
export function puedeEscribirHistoria(rol: Rol | null): boolean {
  return rol !== null && puedeAcceder(rol, 'historia-clinica', 'escritura');
}

/**
 * Agendar, reprogramar y cancelar turnos es de DUENIO y PERSONAL; el
 * VETERINARIO solo atiende los suyos. Se reutiliza la sección de reservas,
 * que tiene el mismo reparto de roles, para no comparar roles a mano.
 */
export function puedeCrearTurnos(rol: Rol | null): boolean {
  return rol !== null && puedeAcceder(rol, 'nueva-reserva', 'escritura');
}

/**
 * El costo acordado con un externo es información de finanzas: solo DUENIO
 * (RN-40 y matriz de acceso). Se reutiliza la sección Panel.
 */
export function puedeVerCostoExterno(rol: Rol | null): boolean {
  return rol !== null && puedeAcceder(rol, 'panel', 'escritura');
}

export function usePuedeEscribirHistoria(): boolean {
  const { sesion } = useAuth();

  return puedeEscribirHistoria(sesion?.rol ?? null);
}
