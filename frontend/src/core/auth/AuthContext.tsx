import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';

import {
  borrarSesion,
  EVENTO_SESION_EXPIRADA,
  guardarSesion,
  leerSesion,
  type Sesion,
} from './almacenSesion';
import { AuthContext, type Credenciales } from './contexto';
import { cerrarSesionApi, iniciarSesionApi, solicitarUsuarioActual } from './servicioAuth';

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

  // Revalida contra el backend la sesión guardada en localStorage: token
  // vencido, usuario desactivado, rol cambiado o restos del login mock.
  useEffect(() => {
    const guardada = leerSesion();

    if (!guardada) {
      return;
    }

    let activo = true;

    solicitarUsuarioActual()
      .then((usuario) => {
        if (!activo) {
          return;
        }

        const sincronizada: Sesion = {
          token: guardada.token,
          rol: usuario.rol,
          usuario: usuario.username,
        };

        guardarSesion(sincronizada);
        setSesion((actual) =>
          actual && actual.token === guardada.token ? sincronizada : actual,
        );
      })
      .catch(() => {
        // Un 401 ya disparó EVENTO_SESION_EXPIRADA. Ante un error de red se
        // conserva la sesión local para no expulsar al usuario sin conexión.
      });

    return () => {
      activo = false;
    };
  }, []);

  const iniciarSesion = useCallback(async (credenciales: Credenciales) => {
    const usuario = credenciales.usuario.trim();

    if (!usuario || credenciales.password.length === 0) {
      throw new Error('Ingresá usuario y contraseña.');
    }

    const { token, rol } = await iniciarSesionApi({
      username: usuario,
      password: credenciales.password,
    });

    const nuevaSesion: Sesion = { token, rol, usuario };

    guardarSesion(nuevaSesion);
    setSesion(nuevaSesion);
  }, []);

  const cerrarSesion = useCallback(() => {
    const token = sesion?.token;

    borrarSesion();
    setSesion(null);

    if (token) {
      void cerrarSesionApi(token).catch(() => undefined);
    }
  }, [sesion]);

  const valor = useMemo(
    () => ({ sesion, iniciarSesion, cerrarSesion }),
    [sesion, iniciarSesion, cerrarSesion],
  );

  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>;
}
