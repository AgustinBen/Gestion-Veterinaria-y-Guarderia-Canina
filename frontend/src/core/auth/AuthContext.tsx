import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';

import {
  borrarSesion,
  EVENTO_SESION_EXPIRADA,
  guardarSesion,
  leerSesion,
  type Sesion,
} from './almacenSesion';
import { AuthContext, type Credenciales } from './contexto';
import { leerRolMock, leerTokenMock, leerUsuarioMock } from './mock';

type Props = {
  children: ReactNode;
};

export function AuthProvider({ children }: Props) {
  const [sesion, setSesion] = useState<Sesion | null>(() => leerSesion());

  useEffect(() => {
    const manejarSesionExpirada = () => {
      setSesion(null);
    };

    window.addEventListener(EVENTO_SESION_EXPIRADA, manejarSesionExpirada);

    return () => {
      window.removeEventListener(EVENTO_SESION_EXPIRADA, manejarSesionExpirada);
    };
  }, []);

  const iniciarSesion = useCallback(async (credenciales: Credenciales) => {
    if (!credenciales.usuario.trim() || credenciales.password.length === 0) {
      throw new Error('Ingresá usuario y contraseña.');
    }

    // Mock provisorio hasta T-10: el rol sale de VITE_MOCK_ROL.
    const rol = leerRolMock();
    const nuevaSesion: Sesion = {
      token: leerTokenMock(),
      rol,
      usuario: leerUsuarioMock(rol),
    };

    guardarSesion(nuevaSesion);
    setSesion(nuevaSesion);
  }, []);

  const cerrarSesion = useCallback(() => {
    borrarSesion();
    setSesion(null);
  }, []);

  const valor = useMemo(
    () => ({ sesion, iniciarSesion, cerrarSesion }),
    [sesion, iniciarSesion, cerrarSesion],
  );

  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>;
}
