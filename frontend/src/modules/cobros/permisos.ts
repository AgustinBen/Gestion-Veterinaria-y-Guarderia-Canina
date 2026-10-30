import { useAuth } from '../../core/auth/contexto';
import { puedeAcceder, type Rol } from '../../core/auth/permisos';

/**
 * RN-22: bajar el precio de un cargo solo lo puede hacer el Dueño. Subir lo
 * puede hacer cualquier rol con acceso a cobros. La regla vive acá para que las
 * pantallas no comparen roles a mano; el backend sigue siendo la autoridad.
 */
const ROLES_QUE_PUEDEN_BAJAR_PRECIO: ReadonlySet<Rol> = new Set<Rol>(['DUENIO']);

export function puedeBajarPrecio(rol: Rol): boolean {
  return ROLES_QUE_PUEDEN_BAJAR_PRECIO.has(rol);
}

export function usePuedeBajarPrecio(): boolean {
  const { sesion } = useAuth();

  return sesion ? puedeBajarPrecio(sesion.rol) : false;
}

/**
 * El listado global de deudores es información financiera: solo el Dueño.
 * Personal conserva el acceso a Cobros y ve la deuda dentro de la cuenta del
 * cliente, pero no el listado completo (RN-40).
 */
export function usePuedeVerDeudores(): boolean {
  const { sesion } = useAuth();

  return sesion ? puedeAcceder(sesion.rol, 'deudores') : false;
}
