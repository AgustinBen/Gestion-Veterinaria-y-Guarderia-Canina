import { createContext, useContext } from 'react';

import type { Sesion } from './almacenSesion';

export type Credenciales = {
  usuario: string;
  password: string;
};

export type ValorAuth = {
  sesion: Sesion | null;
  iniciarSesion: (credenciales: Credenciales) => Promise<void>;
  cerrarSesion: () => void;
};

export const AuthContext = createContext<ValorAuth | null>(null);

export function useAuth(): ValorAuth {
  const contexto = useContext(AuthContext);

  if (!contexto) {
    throw new Error('useAuth debe usarse dentro de <AuthProvider>');
  }

  return contexto;
}
