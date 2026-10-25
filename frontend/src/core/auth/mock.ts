import { etiquetaRol, ROLES, esRol, type Rol } from './permisos';

const ROL_POR_DEFECTO: Rol = 'DUENIO';
const TOKEN_POR_DEFECTO = 'token-mock';

/**
 * Login provisorio hasta T-10. El rol se configura con VITE_MOCK_ROL
 * (ver frontend/.env.example). Al cambiarlo hay que reiniciar `npm run dev`.
 */
export function leerRolMock(): Rol {
  const crudo = import.meta.env.VITE_MOCK_ROL?.trim().toUpperCase();

  if (!crudo) {
    return ROL_POR_DEFECTO;
  }

  if (!esRol(crudo)) {
    throw new Error(
      `VITE_MOCK_ROL inválido: "${crudo}". Valores posibles: ${ROLES.join(', ')}.`,
    );
  }

  return crudo;
}

export function leerTokenMock(): string {
  return import.meta.env.VITE_MOCK_TOKEN?.trim() || TOKEN_POR_DEFECTO;
}

export function leerUsuarioMock(rol: Rol): string {
  return import.meta.env.VITE_MOCK_USUARIO?.trim() || etiquetaRol(rol);
}
