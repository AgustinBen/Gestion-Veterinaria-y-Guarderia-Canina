import { useRef, useState, type FormEvent } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import { ApiError } from '../../core/api/client';
import type { RolUsuarioCreable } from './servicioUsuarios';
import { crearUsuario } from './servicioUsuarios';
import estilos from './CrearCuentaPage.module.css';

type DatosFormulario = {
  username: string;
  password: string;
  rol: RolUsuarioCreable;
};

const FORMULARIO_VACIO: DatosFormulario = {
  username: '',
  password: '',
  rol: 'PERSONAL',
};

function mensajeDeFallo(fallo: unknown): string {
  if (fallo instanceof ApiError) {
    if (fallo.estado === 409) {
      return 'Ese nombre de usuario ya está registrado. Probá con otro.';
    }

    if (fallo.estado === 422) {
      if (fallo.message.startsWith('Error 422 al comunicarse')) {
        return 'Los datos ingresados no son válidos. Revisá el nombre de usuario y la contraseña.';
      }

      return `No se pudieron validar los datos: ${fallo.message}`;
    }

    return fallo.message;
  }

  return fallo instanceof Error ? fallo.message : 'No se pudo crear la cuenta.';
}

export function CrearCuentaPage() {
  const navigate = useNavigate();
  const ubicacion = useLocation();
  const [datos, setDatos] = useState<DatosFormulario>(FORMULARIO_VACIO);
  const [error, setError] = useState<string | null>(null);
  const [confirmacion, setConfirmacion] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const envioEnCurso = useRef(false);

  function volver() {
    if (ubicacion.key === 'default') {
      navigate('/');
      return;
    }

    navigate(-1);
  }

  function actualizar<K extends keyof DatosFormulario>(campo: K, valor: DatosFormulario[K]) {
    setDatos((actuales) => ({ ...actuales, [campo]: valor }));
    setError(null);
    setConfirmacion(null);
  }

  async function manejarEnvio(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();

    if (envioEnCurso.current) {
      return;
    }

    envioEnCurso.current = true;
    setEnviando(true);
    setError(null);
    setConfirmacion(null);

    try {
      const usuario = await crearUsuario(datos);
      setConfirmacion(
        `La cuenta de ${usuario.username} con rol ${usuario.rol === 'PERSONAL' ? 'Personal' : 'Veterinario'} fue creada.`,
      );
      setDatos(FORMULARIO_VACIO);
    } catch (fallo) {
      setError(mensajeDeFallo(fallo));
    } finally {
      envioEnCurso.current = false;
      setEnviando(false);
    }
  }

  return (
    <section className={estilos.pagina} aria-labelledby="crear-cuenta-titulo">
      <div className={estilos.contenido}>
        <button className={estilos.botonVolver} onClick={volver} type="button">
          <span aria-hidden="true">←</span>
          Volver
        </button>

        <header className={estilos.encabezado}>
          <p className={estilos.eyebrow}>Usuarios</p>
          <h1 id="crear-cuenta-titulo">Crear cuenta</h1>
          <p className={estilos.descripcion}>
            Creá una cuenta para el personal de recepción o veterinaria.
          </p>
        </header>

        <form className={estilos.formulario} onSubmit={manejarEnvio}>
          <div className={estilos.campo}>
            <label htmlFor="nuevo-username">Nombre de usuario</label>
            <input
              autoComplete="username"
              id="nuevo-username"
              maxLength={50}
              name="username"
              required
              type="text"
              value={datos.username}
              onChange={(evento) => actualizar('username', evento.target.value)}
            />
          </div>

          <div className={estilos.campo}>
            <label htmlFor="nueva-password">Contraseña</label>
            <input
              autoComplete="new-password"
              id="nueva-password"
              name="password"
              required
              type="password"
              value={datos.password}
              onChange={(evento) => actualizar('password', evento.target.value)}
            />
          </div>

          <div className={estilos.campo}>
            <label htmlFor="nuevo-rol">Rol</label>
            <select
              id="nuevo-rol"
              name="rol"
              required
              value={datos.rol}
              onChange={(evento) => {
                const rol = evento.target.value;
                if (rol === 'PERSONAL' || rol === 'VETERINARIO') {
                  actualizar('rol', rol);
                }
              }}
            >
              <option value="PERSONAL">Personal</option>
              <option value="VETERINARIO">Veterinario</option>
            </select>
          </div>

          {error ? (
            <p className={estilos.error} role="alert">
              {error}
            </p>
          ) : null}
          {confirmacion ? (
            <p className={estilos.confirmacion} role="status">
              {confirmacion}
            </p>
          ) : null}

          <button className={estilos.boton} disabled={enviando} type="submit">
            {enviando ? 'Creando cuenta…' : 'Crear cuenta'}
          </button>
        </form>
      </div>
    </section>
  );
}
