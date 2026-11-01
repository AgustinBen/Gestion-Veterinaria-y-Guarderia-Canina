import { useState, type FormEvent } from 'react';
import { Navigate, useLocation } from 'react-router-dom';

import { useAuth } from '../../core/auth/contexto';
import { rutaInicial } from '../../core/auth/permisos';
import { ApiError } from '../../core/api/client';
import { PatitaIcon } from '../../core/components/PatitaIcon';
import estilos from './LoginPage.module.css';


function leerDestino(state: unknown): string | null {
  if (typeof state !== 'object' || state === null || !('desde' in state)) {
    return null;
  }

  const desde = (state as { desde?: unknown }).desde;

  return typeof desde === 'string' && desde.startsWith('/') ? desde : null;
}

export function LoginPage() {
  const { sesion, iniciarSesion } = useAuth();
  const ubicacion = useLocation();
  const [usuario, setUsuario] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const destino = leerDestino(ubicacion.state) ?? (sesion ? rutaInicial(sesion.rol) : null);

  if (sesion && destino) {
    return <Navigate to={destino} replace />;
  }

  async function manejarEnvio(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    setError(null);
    setEnviando(true);

    try {
      await iniciarSesion({ usuario, password });
    } catch (fallo) {
      if (fallo instanceof ApiError && fallo.estado === 401) {
        setError('Usuario o contraseña incorrectos.');
        return;
      }
      setError(fallo instanceof Error ? fallo.message : 'No se pudo iniciar sesión.');
    } finally {
      setEnviando(false);
    }
  }

  return (
    <main className={estilos.pagina}>
      <section className={estilos.tarjeta} aria-labelledby="login-titulo">
        <div className={estilos.marca}>
          <span
            className={`${estilos.logo} ${enviando ? estilos.logoIngresando : ''}`}
            aria-hidden="true"
          >
            <PatitaIcon />
          </span>
          <div>
            <p className={estilos.nombreMarca}>Huellitas</p>
            <p className={estilos.bajada}>Veterinaria y guardería</p>
          </div>
        </div>

        <h1 id="login-titulo">Iniciar sesión</h1>
        <p className={estilos.texto}>Ingresá con tu usuario y contraseña para entrar al sistema.</p>

        <form className={estilos.formulario} onSubmit={manejarEnvio}>
          <div className={estilos.campo}>
            <label htmlFor="usuario">Usuario</label>
            <input
              id="usuario"
              name="usuario"
              type="text"
              autoComplete="username"
              value={usuario}
              onChange={(evento) => setUsuario(evento.target.value)}
              required
            />
          </div>

          <div className={estilos.campo}>
            <label htmlFor="password">Contraseña</label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(evento) => setPassword(evento.target.value)}
              required
            />
          </div>

          {error ? (
            <p className={estilos.error} role="alert">
              {error}
            </p>
          ) : null}

          <button className={estilos.boton} type="submit" disabled={enviando}>
            {enviando ? 'Ingresando…' : 'Ingresar'}
          </button>
        </form>
      </section>
    </main>
  );
}
