import { useEffect, useState, type FormEvent } from 'react';

import {
  actualizarConfiguracionCupo,
  mensajeDeError,
  obtenerConfiguracionCupo,
} from '../api';
import type { ConfiguracionCupo, Franja } from '../tipos';
import estilos from './ConfiguracionCupo.module.css';

const ETIQUETAS_FRANJA: Record<Franja, string> = {
  DIA: 'Día',
  NOCHE: 'Noche',
};

function fechaLegible(fecha: string): string {
  return new Intl.DateTimeFormat('es-AR', { dateStyle: 'long' }).format(
    new Date(`${fecha}T12:00:00`),
  );
}

export function ConfiguracionCupo() {
  const [configuracion, setConfiguracion] = useState<ConfiguracionCupo | null>(null);
  const [cupoIngresado, setCupoIngresado] = useState('');
  const [cargando, setCargando] = useState(true);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState('');
  const [confirmacion, setConfirmacion] = useState('');
  const [reintento, setReintento] = useState(0);

  useEffect(() => {
    const controlador = new AbortController();

    obtenerConfiguracionCupo({ signal: controlador.signal })
      .then((resultado) => {
        setConfiguracion(resultado);
        setCupoIngresado(String(resultado.cupo_maximo));
      })
      .catch((fallo: unknown) => {
        if (!controlador.signal.aborted) {
          setError(mensajeDeError(fallo));
        }
      })
      .finally(() => {
        if (!controlador.signal.aborted) {
          setCargando(false);
        }
      });

    return () => controlador.abort();
  }, [reintento]);

  async function guardar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    if (!configuracion || guardando) {
      return;
    }

    const valor = Number(cupoIngresado);
    if (
      !Number.isInteger(valor) ||
      valor < configuracion.cupo_minimo ||
      valor > configuracion.cupo_maximo_permitido
    ) {
      setError(
        `Ingresá un entero entre ${configuracion.cupo_minimo} y ${configuracion.cupo_maximo_permitido}.`,
      );
      setConfirmacion('');
      return;
    }

    setGuardando(true);
    setError('');
    setConfirmacion('');
    try {
      const resultado = await actualizarConfiguracionCupo(valor);
      setConfiguracion(resultado);
      setCupoIngresado(String(resultado.cupo_maximo));
      setConfirmacion(
        'Cupo actualizado. La disponibilidad del calendario y de las nuevas reservas ya usa este valor.',
      );
    } catch (fallo: unknown) {
      setError(mensajeDeError(fallo));
    } finally {
      setGuardando(false);
    }
  }

  return (
    <section className={estilos.pagina} aria-labelledby="titulo-configuracion-cupo">
      <header className={estilos.encabezado}>
        <p className={estilos.antetitulo}>Administración · Guardería</p>
        <h1 id="titulo-configuracion-cupo">Configuración del cupo</h1>
        <p className={estilos.descripcion}>
          Definí el máximo de plazas por fecha y franja. El cambio no cancela ni
          elimina reservas existentes.
        </p>
      </header>

      {cargando ? (
        <p className={estilos.estado} role="status">
          Cargando configuración…
        </p>
      ) : error && !configuracion ? (
        <div className={estilos.error} role="alert">
          <p>No pudimos cargar la configuración: {error}</p>
          <button
            className={estilos.botonSecundario}
            onClick={() => {
              setCargando(true);
              setError('');
              setReintento((actual) => actual + 1);
            }}
            type="button"
          >
            Reintentar
          </button>
        </div>
      ) : configuracion ? (
        <>
          <form className={estilos.formulario} onSubmit={guardar}>
            <label className={estilos.etiqueta} htmlFor="cupo-maximo">
              Cupo máximo por fecha y franja
            </label>
            <p className={estilos.ayuda} id="ayuda-cupo-maximo">
              Permitido: {configuracion.cupo_minimo} a{' '}
              {configuracion.cupo_maximo_permitido} plazas.
            </p>
            <input
              aria-describedby="ayuda-cupo-maximo"
              id="cupo-maximo"
              max={configuracion.cupo_maximo_permitido}
              min={configuracion.cupo_minimo}
              name="cupo-maximo"
              required
              step="1"
              type="number"
              value={cupoIngresado}
              onChange={(evento) => {
                setCupoIngresado(evento.target.value);
                setError('');
              }}
            />
            <button
              className={estilos.boton}
              disabled={guardando}
              type="submit"
            >
              {guardando ? 'Guardando…' : 'Guardar cupo'}
            </button>
          </form>

          {error ? (
            <p className={estilos.error} role="alert">
              No se pudo guardar el cupo: {error}
            </p>
          ) : null}
          {confirmacion ? (
            <p className={estilos.confirmacion} role="status">
              {confirmacion}
            </p>
          ) : null}

          {configuracion.sobreocupaciones.length > 0 ? (
            <section className={estilos.advertencia} aria-labelledby="titulo-sobrecupo">
              <h2 id="titulo-sobrecupo">Reservas existentes por encima del cupo</h2>
              <p>
                No se canceló ninguna reserva. En estas franjas la disponibilidad
                para nuevas reservas es cero; el exceso se informa en el calendario.
              </p>
              <ul>
                {configuracion.sobreocupaciones.map((franja) => (
                  <li key={`${franja.fecha}-${franja.franja}`}>
                    {fechaLegible(franja.fecha)} · {ETIQUETAS_FRANJA[franja.franja]}:
                    {' '}{franja.ocupado} ocupadas de {franja.publico} plazas públicas
                    {' '} (exceso de {franja.exceso}).
                  </li>
                ))}
              </ul>
            </section>
          ) : (
            <p className={estilos.confirmacion} role="status">
              No hay franjas ocupadas por encima del cupo configurado.
            </p>
          )}
        </>
      ) : null}
    </section>
  );
}
