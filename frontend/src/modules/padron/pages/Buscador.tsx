import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import {
  buscarPersonas,
  listarPacientes,
  mensajeDeError,
  obtenerPersona,
} from '../api';
import { usePuedeEscribirPadron } from '../permisos';
import type { PacienteResumen, PersonaResumen } from '../tipos';
import estilos from '../padron.module.css';

/** Retraso corto para no saturar la API mientras se escribe. */
const RETRASO_BUSQUEDA_MS = 250;
const MAX_RESULTADOS = 10;
const TAMANIO_PAGINA_PACIENTES = 100;
const TAMANIO_PAGINA_LISTADO = 5;

type ResultadoMascota = {
  tipo: 'paciente';
  paciente: PacienteResumen;
  titulares: PersonaResumen[];
};

type ResultadoPersona = {
  tipo: 'persona';
  persona: PersonaResumen;
};

type Resultado = ResultadoMascota | ResultadoPersona;

type Estado = 'inicial' | 'cargando' | 'listo' | 'error';

type Listado = {
  intento: number;
  estado: Estado;
  filas: PacienteResumen[];
  error: string;
};

async function listarTodosLosPacientes(signal: AbortSignal): Promise<PacienteResumen[]> {
  const pacientes: PacienteResumen[] = [];
  let offset = 0;

  for (;;) {
    const pagina = await listarPacientes({
      signal,
      limite: TAMANIO_PAGINA_PACIENTES,
      offset,
    });

    pacientes.push(...pagina);

    if (pagina.length < TAMANIO_PAGINA_PACIENTES) {
      return pacientes;
    }

    offset += pagina.length;
  }
}

export function Buscador() {
  const puedeEscribir = usePuedeEscribirPadron();
  const [texto, setTexto] = useState('');
  const [consultaAplicada, setConsultaAplicada] = useState<{
    texto: string;
    estado: Estado;
    filas: Resultado[];
    error: string;
  } | null>(null);
  const [reintento, setReintento] = useState(0);
  const [listado, setListado] = useState<Listado>({
    intento: 0,
    estado: 'cargando',
    filas: [],
    error: '',
  });
  const [reintentoListado, setReintentoListado] = useState(0);
  const [paginaListado, setPaginaListado] = useState(1);

  const consulta = texto.trim();
  // Solo se muestra el resultado de la consulta vigente; al cambiar el texto
  // vuelve a "cargando" sin tocar estado desde el efecto.
  const vigente = consultaAplicada?.texto === consulta ? consultaAplicada : null;
  const estado: Estado = !consulta ? 'inicial' : (vigente?.estado ?? 'cargando');
  const resultados = vigente?.filas ?? [];
  const error = vigente?.error ?? '';

  const listadoVigente = listado.intento === reintentoListado ? listado : null;
  const estadoListado: Estado = listadoVigente?.estado ?? 'cargando';
  const pacientesListado = listadoVigente?.filas ?? [];
  const errorListado = listadoVigente?.error ?? '';
  const cantidadPaginas = Math.ceil(pacientesListado.length / TAMANIO_PAGINA_LISTADO);
  const paginaVisible = Math.min(paginaListado, Math.max(cantidadPaginas, 1));
  const indiceInicio = (paginaVisible - 1) * TAMANIO_PAGINA_LISTADO;
  const pacientesVisibles = pacientesListado.slice(
    indiceInicio,
    indiceInicio + TAMANIO_PAGINA_LISTADO,
  );

  useEffect(() => {
    const control = new AbortController();
    let activo = true;

    listarTodosLosPacientes(control.signal)
      .then((pacientes) => {
        if (!activo || control.signal.aborted) {
          return;
        }

        setListado({
          intento: reintentoListado,
          estado: 'listo',
          filas: pacientes,
          error: '',
        });
      })
      .catch((fallo) => {
        if (!activo || control.signal.aborted) {
          return;
        }

        setListado({
          intento: reintentoListado,
          estado: 'error',
          filas: [],
          error: mensajeDeError(fallo),
        });
      });

    return () => {
      activo = false;
      control.abort();
    };
  }, [reintentoListado]);

  useEffect(() => {
    const consulta = texto.trim();

    if (!consulta) {
      return;
    }

    const control = new AbortController();
    const temporizador = window.setTimeout(async () => {
      setConsultaAplicada({ texto: consulta, estado: 'cargando', filas: [], error: '' });

      try {
        const personas = await buscarPersonas(consulta, { signal: control.signal });
        const visibles = personas.slice(0, MAX_RESULTADOS);
        const detalles = await Promise.all(
          visibles.map(async (persona) => ({
            persona,
            mascotas: (await obtenerPersona(persona.id, { signal: control.signal })).mascotas,
          })),
        );

        if (control.signal.aborted) {
          return;
        }

        const pacientesPorId = new Map<number, ResultadoMascota>();
        const titularesSinMascotas: Resultado[] = [];

        detalles.forEach(({ persona, mascotas }) => {

          if (mascotas.length === 0) {
            titularesSinMascotas.push({ tipo: 'persona', persona });
            return;
          }

          mascotas.forEach((paciente) => {
            const resultado = pacientesPorId.get(paciente.id);

            if (resultado) {
              if (!resultado.titulares.some((titular) => titular.id === persona.id)) {
                resultado.titulares.push(persona);
              }
            } else {
              pacientesPorId.set(paciente.id, {
                tipo: 'paciente',
                paciente,
                titulares: [persona],
              });
            }
          });
        });

        setConsultaAplicada({
          texto: consulta,
          estado: 'listo',
          filas: [...pacientesPorId.values(), ...titularesSinMascotas].slice(
            0,
            MAX_RESULTADOS,
          ),
          error: '',
        });
      } catch (fallo) {
        if (control.signal.aborted) {
          return;
        }

        setConsultaAplicada({
          texto: consulta,
          estado: 'error',
          filas: [],
          error: mensajeDeError(fallo),
        });
      }
    }, RETRASO_BUSQUEDA_MS);

    return () => {
      window.clearTimeout(temporizador);
      control.abort();
    };
  }, [texto, reintento]);

  return (
    <section className={estilos.pagina} aria-labelledby="titulo-padron">
      <div className={estilos.cabecera}>
        <div>
          <p className={estilos.antetitulo}>Padrón de clientes</p>
          <h1 className={estilos.titulo} id="titulo-padron">
            Dueños y mascotas
          </h1>
          <p className={estilos.subtitulo}>
            Buscá por nombre, DNI, teléfono o nombre de la mascota.
          </p>
        </div>

        {puedeEscribir ? (
          <div className={estilos.acciones}>
            <Link className={estilos.boton} to="/padron/alta-persona">
              Nuevo dueño
            </Link>
          </div>
        ) : null}
      </div>

      <div className={estilos.campo}>
        <label className="sr-only" htmlFor="padron-busqueda">
          Buscar
        </label>
        <input
          autoComplete="off"
          id="padron-busqueda"
          onChange={(evento) => setTexto(evento.target.value)}
          placeholder="Ej.: Ana, 30111222, Firulais"
          type="search"
          value={texto}
        />
      </div>

      {estado === 'cargando' ? (
        <p className={estilos.cargando} role="status">
          Buscando…
        </p>
      ) : null}

      {estado === 'error' ? (
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

      {estado === 'listo' && resultados.length === 0 ? (
        <p className={estilos.vacio}>No encontramos dueños ni mascotas con ese dato.</p>
      ) : null}

      {resultados.length > 0 ? (
        <ul className={estilos.resultados}>
          {resultados.map((resultado) => (
            <li
              key={
                resultado.tipo === 'paciente'
                  ? `paciente-${resultado.paciente.id}`
                  : `persona-${resultado.persona.id}`
              }
            >
              <Link
                className={estilos.resultado}
                to={
                  resultado.tipo === 'paciente'
                    ? `/padron/paciente/${resultado.paciente.id}`
                    : `/padron/persona/${resultado.persona.id}`
                }
              >
                <span className={estilos.fila}>
                  <strong>
                    {resultado.tipo === 'paciente'
                      ? resultado.paciente.nombre
                      : `${resultado.persona.apellido}, ${resultado.persona.nombre}`}
                  </strong>
                  {resultado.tipo === 'paciente' ? (
                    <span className={estilos.insignia}>
                      {resultado.paciente.especie_nombre}
                    </span>
                  ) : resultado.persona.dni_pendiente ? (
                    <span className={`${estilos.insignia} ${estilos.insigniaAviso}`}>
                      DNI pendiente
                    </span>
                  ) : null}
                </span>

                {resultado.tipo === 'paciente' ? (
                  <span className={estilos.textoSuave}>
                    {resultado.titulares.length > 0
                      ? `Persona vinculada: ${resultado.titulares
                          .map((titular) => `${titular.apellido}, ${titular.nombre}`)
                          .join(' · ')}`
                      : 'Titular no disponible'}
                  </span>
                ) : (
                  <span className={estilos.textoSuave}>
                    {resultado.persona.telefonos.length > 0
                      ? `Teléfono: ${resultado.persona.telefonos.join(' · ')}`
                      : 'Sin teléfono registrado'}
                  </span>
                )}
              </Link>
            </li>
          ))}
        </ul>
      ) : null}

      {!consulta ? (
        <section className={estilos.listado} aria-labelledby="titulo-pacientes">
          <div className={estilos.cabecera}>
            <div>
              <h2 className={estilos.tituloSeccion} id="titulo-pacientes">
                Mascotas registradas
              </h2>
            </div>
            {estadoListado === 'listo' ? (
              <span className={estilos.insignia}>{pacientesListado.length}</span>
            ) : null}
          </div>

          {estadoListado === 'cargando' ? (
            <p className={estilos.cargando} role="status">
              Cargando mascotas…
            </p>
          ) : null}

          {estadoListado === 'error' ? (
            <div className={estilos.error} role="alert">
              <p>{errorListado}</p>
              <div>
                <button
                  className={`${estilos.boton} ${estilos.botonSecundario}`}
                  onClick={() => {
                    setPaginaListado(1);
                    setReintentoListado((valor) => valor + 1);
                  }}
                  type="button"
                >
                  Reintentar
                </button>
              </div>
            </div>
          ) : null}

          {estadoListado === 'listo' && pacientesListado.length === 0 ? (
            <p className={estilos.vacio}>Todavía no hay mascotas registradas.</p>
          ) : null}

          {pacientesListado.length > 0 ? (
            <ul className={estilos.resultados}>
              {pacientesVisibles.map((paciente) => (
                <li key={paciente.id}>
                  <Link
                    className={`${estilos.resultado} ${estilos.resultadoMascota}`}
                    to={`/padron/paciente/${paciente.id}`}
                  >
                    <span className={estilos.avatarMascota} aria-hidden="true">
                      {paciente.nombre.charAt(0)}
                    </span>
                    <span className={estilos.contenidoMascota}>
                      <span className={estilos.fila}>
                        <strong>{paciente.nombre}</strong>
                        <span className={estilos.insignia}>
                          {paciente.especie_nombre}
                        </span>
                      </span>
                      <span className={estilos.textoSuave}>
                        {paciente.raza_nombre
                          ? `Raza: ${paciente.raza_nombre}`
                          : 'Sin raza registrada'}
                      </span>
                    </span>
                    <span className={estilos.accionMascota}>
                      Ver ficha completa
                      <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                        <path d="m9 18 6-6-6-6" />
                      </svg>
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          ) : null}

          {cantidadPaginas > 1 ? (
            <nav className={estilos.paginacion} aria-label="Paginación de mascotas">
              <div className={estilos.controlesPaginacion}>
                <button
                  aria-label="Página anterior"
                  className={estilos.botonPaginacion}
                  disabled={paginaVisible === 1}
                  onClick={() => setPaginaListado(paginaVisible - 1)}
                  type="button"
                >
                  Anterior
                </button>
                <span aria-current="page" className={estilos.indicadorPagina}>
                  Página {paginaVisible} de {cantidadPaginas}
                </span>
                <button
                  aria-label="Página siguiente"
                  className={estilos.botonPaginacion}
                  disabled={paginaVisible === cantidadPaginas}
                  onClick={() => setPaginaListado(paginaVisible + 1)}
                  type="button"
                >
                  Siguiente
                </button>
              </div>
            </nav>
          ) : null}
        </section>
      ) : null}
    </section>
  );
}
