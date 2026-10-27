import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { mensajeDeError, obtenerPaciente, obtenerTitulares } from '../api';
import { usePuedeEscribirPadron } from '../permisos';
import type { PacienteDetalle, TitularVigente } from '../tipos';
import estilos from '../padron.module.css';

function textoEdad(edadAnios: number | null, edadMeses: number | null): string {
  if (edadAnios === null && edadMeses === null) {
    return 'Sin fecha de nacimiento';
  }

  const partes: string[] = [];

  if (edadAnios !== null && edadAnios > 0) {
    partes.push(`${edadAnios} ${edadAnios === 1 ? 'año' : 'años'}`);
  }

  if (edadMeses !== null && edadMeses > 0) {
    partes.push(`${edadMeses} ${edadMeses === 1 ? 'mes' : 'meses'}`);
  }

  return partes.length > 0 ? partes.join(' ') : 'Menos de 1 mes';
}

export function FichaPaciente() {
  const { id } = useParams();
  const pacienteId = Number(id);
  const puedeEscribir = usePuedeEscribirPadron();
  const [paciente, setPaciente] = useState<PacienteDetalle | null>(null);
  const [titulares, setTitulares] = useState<TitularVigente[]>([]);
  const [error, setError] = useState('');
  const [reintento, setReintento] = useState(0);

  useEffect(() => {
    let activo = true;

    obtenerPaciente(pacienteId)
      .then(async (detalle) => {
        if (!activo) {
          return;
        }

        const vigentes = await obtenerTitulares(pacienteId).catch(() => []);

        if (activo) {
          setError('');
          setPaciente(detalle);
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

  if (!paciente) {
    return (
      <section className={estilos.pagina}>
        <p className={estilos.cargando} role="status">
          Cargando ficha…
        </p>
      </section>
    );
  }

  const principal = titulares.find((titular) => titular.principal);

  return (
    <section className={estilos.pagina} aria-labelledby="titulo-ficha-paciente">
      <div className={estilos.cabecera}>
        <div>
          <h1 className={estilos.titulo} id="titulo-ficha-paciente">
            {paciente.nombre}
          </h1>
          <p className={estilos.subtitulo}>Ficha de mascota</p>
        </div>

        {puedeEscribir ? (
          <div className={estilos.acciones}>
            <Link
              className={`${estilos.boton} ${estilos.botonSecundario}`}
              to={`/padron/paciente/${paciente.id}/editar`}
            >
              Editar
            </Link>
          </div>
        ) : null}
      </div>

      <div className={estilos.tarjeta}>
        <dl className={estilos.datos}>
          <div className={estilos.dato}>
            <dt>Especie</dt>
            <dd>{paciente.especie_nombre}</dd>
          </div>
          <div className={estilos.dato}>
            <dt>Raza</dt>
            <dd>{paciente.raza_nombre ?? 'Sin raza'}</dd>
          </div>
          <div className={estilos.dato}>
            <dt>Tamaño</dt>
            <dd>{paciente.tamanio_nombre ?? 'Sin tamaño'}</dd>
          </div>
          <div className={estilos.dato}>
            <dt>Peso</dt>
            <dd>{paciente.peso_kg !== null ? `${paciente.peso_kg} kg` : 'Sin peso'}</dd>
          </div>
          <div className={estilos.dato}>
            <dt>Edad calculada</dt>
            <dd>{textoEdad(paciente.edad_anios, paciente.edad_meses)}</dd>
          </div>
          <div className={estilos.dato}>
            <dt>Castrado</dt>
            <dd>
              {paciente.castrado === null ? 'Sin dato' : paciente.castrado ? 'Sí' : 'No'}
            </dd>
          </div>
        </dl>
      </div>

      <div className={estilos.tarjeta}>
        <div className={estilos.cabecera}>
          <h2>Titulares</h2>
          <Link
            className={estilos.enlace}
            to={`/padron/paciente/${paciente.id}/titulares`}
          >
            Ver historial de titulares
          </Link>
        </div>

        {principal ? (
          <p className={estilos.fila}>
            <span>
              {principal.apellido}, {principal.nombre}
            </span>
            <span className={estilos.insignia}>Principal</span>
            <span className={estilos.textoSuave}>{principal.tipo}</span>
          </p>
        ) : (
          <p className={estilos.textoSuave}>Sin titular principal registrado.</p>
        )}
      </div>

      <Link className={estilos.enlace} to="/padron">
        Volver a la búsqueda
      </Link>
    </section>
  );
}
