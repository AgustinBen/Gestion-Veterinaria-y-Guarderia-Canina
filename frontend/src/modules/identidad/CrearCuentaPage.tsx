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

const OPCIONES_ROL: {
  valor: RolUsuarioCreable;
  etiqueta: string;
  descripcion: string;
}[] = [
  {
    valor: 'PERSONAL',
    etiqueta: 'Personal',
    descripcion: 'Reservas, guardería y atención diaria.',
  },
  {
    valor: 'VETERINARIO',
    etiqueta: 'Veterinario',
    descripcion: 'Historias clínicas y turnos médicos.',
  },
];

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
        <header className={estilos.encabezado}>
          <p className={estilos.eyebrow}>Administración</p>
          <h1 id="crear-cuenta-titulo">Crear cuenta</h1>
          <p className={estilos.descripcion}>
            Sumá a alguien nuevo al equipo de Huellitas.
          </p>
        </header>

        <form className={estilos.formulario} onSubmit={manejarEnvio}>
          <div className={estilos.encabezadoFormulario}>
            <span className={estilos.iconoEncabezado} aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none">
                <circle cx="7.5" cy="15.5" r="5.5" />
                <path d="m11.5 11.5 9-9 2 2-2 2 1.5 1.5-2.5 2.5-1.5-1.5-4 4M7.5 15.5h.01" />
              </svg>
            </span>
            <div>
              <h2>Datos de acceso</h2>
              <p>Con estos datos va a poder ingresar al sistema.</p>
            </div>
          </div>

          <div className={estilos.campo}>
            <label htmlFor="nuevo-username">Usuario</label>
            <input
              autoComplete="off"
              id="nuevo-username"
              maxLength={50}
              name="username"
              placeholder="Ej. mariana.lopez"
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
              placeholder="Ingresá una contraseña"
              required
              type="password"
              value={datos.password}
              onChange={(evento) => actualizar('password', evento.target.value)}
            />
          </div>

          <fieldset className={estilos.selectorRol}>
            <legend>Rol</legend>
            <div className={estilos.opcionesRol}>
              {OPCIONES_ROL.map((opcion) => {
                const seleccionado = datos.rol === opcion.valor;

                return (
                  <label
                    className={`${estilos.opcionRol} ${
                      seleccionado ? estilos.opcionRolSeleccionada : ''
                    }`}
                    key={opcion.valor}
                  >
                    <input
                      checked={seleccionado}
                      className={estilos.radioOculto}
                      name="rol"
                      type="radio"
                      value={opcion.valor}
                      onChange={() => actualizar('rol', opcion.valor)}
                    />
                    <span className={estilos.iconoRol} aria-hidden="true">
                      {opcion.valor === 'PERSONAL' ? (
                        <svg viewBox="0 0 24 24" fill="none">
                          <circle cx="12" cy="8" r="4" />
                          <path d="M4 21a8 8 0 0 1 16 0" />
                        </svg>
                      ) : (
                        <svg viewBox="0 0 24 24" fill="none">
                          <path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z" />
                          <path d="M12 8v6m-3-3h6" />
                        </svg>
                      )}
                    </span>
                    <span className={estilos.detalleRol}>
                      <strong>{opcion.etiqueta}</strong>
                      <small>{opcion.descripcion}</small>
                    </span>
                    {seleccionado ? (
                      <svg
                        className={estilos.confirmacionRol}
                        viewBox="0 0 24 24"
                        fill="none"
                        aria-hidden="true"
                      >
                        <path d="m5 12 4 4L19 6" />
                      </svg>
                    ) : null}
                  </label>
                );
              })}
            </div>
          </fieldset>

          {error ? (
            <p className={estilos.error} role="alert">
              {error}
            </p>
          ) : null}

          <div className={estilos.accionesFormulario}>
            <button
              className={estilos.botonVolverFormulario}
              onClick={volver}
              type="button"
            >
              <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="m15 18-6-6 6-6M9 12h12" />
              </svg>
              Volver
            </button>
            <button
              className={estilos.boton}
              disabled={enviando}
              type="submit"
            >
              {enviando ? (
                'Creando cuenta…'
              ) : (
                <>
                  <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <circle cx="9" cy="8" r="3.5" />
                    <path d="M3 20v-1.2A4.8 4.8 0 0 1 7.8 14h2.4a4.8 4.8 0 0 1 4.8 4.8V20M19 7v6M22 10h-6" />
                  </svg>
                  Crear cuenta
                </>
              )}
            </button>
          </div>

          {confirmacion ? (
            <div className={estilos.confirmacion} role="status">
              <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="m5 12 4 4L19 6" />
              </svg>
              <div>
                <strong>¡Cuenta creada!</strong>
                <span>{confirmacion}</span>
              </div>
            </div>
          ) : null}
        </form>
      </div>
    </section>
  );
}
