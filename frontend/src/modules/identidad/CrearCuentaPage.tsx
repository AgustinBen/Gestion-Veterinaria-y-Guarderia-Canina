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
  nombre: string;
  apellido: string;
  dni: string;
  telefono: string;
  especialidad: string;
};

type Coincidencia = {
  persona: { nombre: string; apellido: string };
  motivo: string;
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
  nombre: '',
  apellido: '',
  dni: '',
  telefono: '',
  especialidad: '',
};

function detalleDe(fallo: unknown): Record<string, unknown> | null {
  if (
    fallo instanceof ApiError &&
    typeof fallo.detalle === 'object' &&
    fallo.detalle !== null
  ) {
    return fallo.detalle as Record<string, unknown>;
  }

  return null;
}

function mensajeDeFallo(fallo: unknown): string {
  if (fallo instanceof ApiError) {
    if (fallo.estado === 409) {
      if (detalleDe(fallo)?.codigo === 'DNI_DUPLICADO') {
        return 'Ya existe una persona con ese DNI. Revisá el dato ingresado.';
      }

      return 'Ese nombre de usuario ya está registrado. Probá con otro.';
    }

    if (fallo.estado === 422) {
      if (fallo.message.startsWith('Error 422 al comunicarse')) {
        return 'Los datos ingresados no son válidos. Revisá los datos de acceso y los del empleado.';
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
  const [coincidencias, setCoincidencias] = useState<Coincidencia[]>([]);
  const [duplicadoConfirmado, setDuplicadoConfirmado] = useState(false);
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
    setCoincidencias([]);
    setDuplicadoConfirmado(false);
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
      const especialidad = datos.especialidad.trim();
      const usuario = await crearUsuario({
        username: datos.username,
        password: datos.password,
        rol: datos.rol,
        empleado: {
          nombre: datos.nombre.trim(),
          apellido: datos.apellido.trim(),
          dni: datos.dni.trim(),
          telefono: datos.telefono.trim(),
          ...(datos.rol === 'VETERINARIO' && especialidad !== ''
            ? { especialidad }
            : {}),
          ...(duplicadoConfirmado ? { confirmar_duplicado: true } : {}),
        },
      });
      setConfirmacion(
        `La cuenta de ${usuario.username} con rol ${usuario.rol === 'PERSONAL' ? 'Personal' : 'Veterinario'} fue creada.`,
      );
      setDatos(FORMULARIO_VACIO);
      setDuplicadoConfirmado(false);
    } catch (fallo) {
      const detalle = detalleDe(fallo);
      if (detalle?.codigo === 'POSIBLE_DUPLICADO') {
        setCoincidencias(
          Array.isArray(detalle.coincidencias)
            ? (detalle.coincidencias as Coincidencia[])
            : [],
        );
        setDuplicadoConfirmado(false);
      } else {
        setError(mensajeDeFallo(fallo));
      }
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

          <div className={estilos.campo}>
            <label htmlFor="empleado-nombre">Nombre</label>
            <input
              autoComplete="off"
              id="empleado-nombre"
              required={true}
              type="text"
              value={datos.nombre}
              onChange={(evento) => actualizar('nombre', evento.target.value)}
            />
          </div>

          <div className={estilos.campo}>
            <label htmlFor="empleado-apellido">Apellido</label>
            <input
              autoComplete="off"
              id="empleado-apellido"
              required={true}
              type="text"
              value={datos.apellido}
              onChange={(evento) => actualizar('apellido', evento.target.value)}
            />
          </div>

          <div className={estilos.campo}>
            <label htmlFor="empleado-dni">DNI</label>
            <input
              autoComplete="off"
              id="empleado-dni"
              inputMode="numeric"
              required={true}
              type="text"
              value={datos.dni}
              onChange={(evento) => actualizar('dni', evento.target.value)}
            />
          </div>

          <div className={estilos.campo}>
            <label htmlFor="empleado-telefono">Teléfono</label>
            <input
              autoComplete="off"
              id="empleado-telefono"
              inputMode="tel"
              required={true}
              type="text"
              value={datos.telefono}
              onChange={(evento) => actualizar('telefono', evento.target.value)}
            />
          </div>

          {datos.rol === 'VETERINARIO' ? (
            <div className={estilos.campo}>
              <label htmlFor="empleado-especialidad">Especialidad (opcional)</label>
              <input
                autoComplete="off"
                id="empleado-especialidad"
                maxLength={45}
                required={false}
                type="text"
                value={datos.especialidad}
                onChange={(evento) => actualizar('especialidad', evento.target.value)}
              />
            </div>
          ) : null}

          {coincidencias.length > 0 ? (
            <div className={estilos.error} role="alert">
              <p>Puede que esta persona ya esté registrada:</p>
              <ul>
                {coincidencias.map((coincidencia, indice) => (
                  <li key={indice}>
                    {coincidencia.persona.nombre} {coincidencia.persona.apellido} —{' '}
                    {coincidencia.motivo}
                  </li>
                ))}
              </ul>
              <label>
                <input
                  checked={duplicadoConfirmado}
                  onChange={(evento) => setDuplicadoConfirmado(evento.target.checked)}
                  type="checkbox"
                />{' '}
                Confirmo que es otra persona
              </label>
            </div>
          ) : null}

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
              disabled={enviando || (coincidencias.length > 0 && !duplicadoConfirmado)}
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
