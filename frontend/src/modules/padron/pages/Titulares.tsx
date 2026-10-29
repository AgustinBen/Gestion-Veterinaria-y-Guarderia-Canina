import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { mensajeDeError, obtenerTitulares } from '../api';
import type { TitularVigente } from '../tipos';
import estilos from '../padron.module.css';

export function Titulares() {
  const { id } = useParams();
  const pacienteId = Number(id);
  const [titulares, setTitulares] = useState<TitularVigente[]>([]);
  const [error, setError] = useState('');
  const [reintento, setReintento] = useState(0);

  useEffect(() => {
    let activo = true;

    obtenerTitulares(pacienteId)
      .then((vigentes) => {
        if (activo) {
          setError('');
          setTitulares(vigentes);
        }
      })
      .catch((fallo) => {
        if (activo) {
          setError(mensajeDeError(fallo));
        }
      });

    return () => {
      activo = false;
    };
  }, [pacienteId, reintento]);

  return (
    <section className={estilos.pagina} aria-labelledby="titulo-titulares">
      <div>
        <h1 className={estilos.titulo} id="titulo-titulares">
          Titulares
        </h1>
        <p className={estilos.subtitulo}>Titulares vigentes de la mascota.</p>
      </div>

      {error ? (
        <div className={estilos.error} role="alert">
          <p>{error}</p>
          <div>
            <button
              className={`${estilos.boton} ${estilos.botonSecundario}`}
              onClick={() => setReintento((valor) => valor + 1)}
              type="button"
            >
              Reintentar
            </button>
          </div>
        </div>
      ) : null}

      {!error && titulares.length === 0 ? (
        <p className={estilos.cargando}>No hay titulares vigentes para esta mascota.</p>
      ) : null}

      {titulares.length > 0 ? (
        <ul className={estilos.lista}>
          {titulares.map((titular) => (
            <li className={estilos.tarjeta} key={`${titular.persona_id}-${titular.desde}`}>
              <span className={estilos.fila}>
                <Link className={estilos.enlace} to={`/padron/persona/${titular.persona_id}`}>
                  {titular.apellido}, {titular.nombre}
                </Link>
                {titular.principal ? <span className={estilos.insignia}>Principal</span> : null}
              </span>
              <span className={estilos.textoSuave}>
                {titular.tipo} · desde {titular.desde}
              </span>
            </li>
          ))}
        </ul>
      ) : null}

      <Link className={estilos.enlace} to={`/padron/paciente/${pacienteId}`}>
        Volver a la ficha de la mascota
      </Link>
    </section>
  );
}
