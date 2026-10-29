import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { mensajeDeError, obtenerPersona } from '../api';
import { usePuedeEscribirPadron } from '../permisos';
import type { Domicilio, PersonaDetalle } from '../tipos';
import estilos from '../padron.module.css';

function formatearDomicilio(domicilio: Domicilio | null): string {
  if (!domicilio) {
    return 'Sin domicilio';
  }

  const partes = [
    [domicilio.calle, domicilio.numero].filter(Boolean).join(' '),
    domicilio.piso ? `Piso ${domicilio.piso}` : '',
    domicilio.departamento ? `Depto. ${domicilio.departamento}` : '',
    domicilio.localidad,
    domicilio.codigo_postal,
    domicilio.referencia,
  ].filter((parte) => Boolean(parte && String(parte).trim()));

  return partes.length > 0 ? partes.join(', ') : 'Sin domicilio';
}

export function FichaPersona() {
  const { id } = useParams();
  const personaId = Number(id);
  const puedeEscribir = usePuedeEscribirPadron();
  const [persona, setPersona] = useState<PersonaDetalle | null>(null);
  const [error, setError] = useState('');
  const [reintento, setReintento] = useState(0);

  useEffect(() => {
    let activo = true;

    obtenerPersona(personaId)
      .then((detalle) => {
        if (activo) {
          setError('');
          setPersona(detalle);
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
  }, [personaId, reintento]);

  if (error) {
    return (
      <section className={estilos.pagina}>
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
        <Link className={estilos.enlace} to="/padron">
          Volver a la búsqueda
        </Link>
      </section>
    );
  }

  if (!persona) {
    return (
      <section className={estilos.pagina}>
        <p className={estilos.cargando} role="status">
          Cargando ficha…
        </p>
      </section>
    );
  }

  return (
    <section className={estilos.pagina} aria-labelledby="titulo-ficha-persona">
      <div className={estilos.cabecera}>
        <div>
          <h1 className={estilos.titulo} id="titulo-ficha-persona">
            {persona.apellido}, {persona.nombre}
          </h1>
          <p className={estilos.subtitulo}>Ficha de dueño</p>
        </div>

        {puedeEscribir ? (
          <div className={estilos.acciones}>
            <Link
              className={`${estilos.boton} ${estilos.botonSecundario}`}
              to={`/padron/persona/${persona.id}/editar`}
            >
              Editar
            </Link>
            <Link className={estilos.boton} to={`/padron/alta-paciente?titular=${persona.id}`}>
              Agregar mascota
            </Link>
          </div>
        ) : null}
      </div>

      {persona.dni_pendiente ? (
        <p className={`${estilos.aviso}`} role="status">
          DNI pendiente: completalo en la próxima visita.
        </p>
      ) : null}

      <div className={estilos.tarjeta}>
        <dl className={estilos.datos}>
          <div className={estilos.dato}>
            <dt>DNI</dt>
            <dd>{persona.dni ?? 'Pendiente'}</dd>
          </div>
          <div className={estilos.dato}>
            <dt>Teléfonos</dt>
            <dd>{persona.telefonos.length > 0 ? persona.telefonos.join(' · ') : 'Sin teléfono'}</dd>
          </div>
          <div className={estilos.dato}>
            <dt>Domicilio</dt>
            <dd>{formatearDomicilio(persona.domicilio)}</dd>
          </div>
        </dl>
      </div>

      <div className={estilos.tarjeta}>
        <div className={estilos.cabecera}>
          <h2>Mascotas</h2>
          <span className={estilos.insignia}>{persona.mascotas.length}</span>
        </div>

        {persona.mascotas.length === 0 ? (
          <p className={estilos.textoSuave}>Todavía no tiene mascotas registradas.</p>
        ) : (
          <ul className={estilos.lista}>
            {persona.mascotas.map((mascota) => (
              <li key={mascota.id}>
                <Link className={estilos.enlace} to={`/padron/paciente/${mascota.id}`}>
                  {mascota.nombre}
                </Link>{' '}
                <span className={estilos.textoSuave}>
                  ({mascota.especie_nombre}
                  {mascota.raza_nombre ? ` / ${mascota.raza_nombre}` : ''})
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <Link className={estilos.enlace} to="/padron">
        Volver a la búsqueda
      </Link>
    </section>
  );
}
