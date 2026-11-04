import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { Alerta } from '../../../core/components/ui/Alerta';
import { Boton } from '../../../core/components/ui/Boton';
import { Paginacion } from '../../../core/components/ui/Paginacion';
import {
  buscarPacientes,
  listarPacientes,
  mensajeDeError,
} from '../../padron/api';
import type { PacienteResumen } from '../../padron/tipos';
import { listarPacientesPorAtencion } from '../api';
import { DuenioMascota } from '../components/DuenioMascota';
import type { CategoriaClinica } from '../tipos';
import estilos from '../clinica.module.css';

type Filtro = 'TODAS' | CategoriaClinica;

const CATEGORIAS: { id: Filtro; etiqueta: string }[] = [
  { id: 'TODAS', etiqueta: 'Todas' },
  { id: 'CONSULTA', etiqueta: 'Consultas' },
  { id: 'VACUNA', etiqueta: 'Vacunas' },
  { id: 'CIRUGIA', etiqueta: 'Cirugías' },
  { id: 'TRATAMIENTO', etiqueta: 'Tratamientos' },
];
const MAX_PACIENTES = 100;
const TAMANIO_PAGINA_PACIENTES = 5;
const RETRASO_BUSQUEDA_MS = 250;

type Estado = 'cargando' | 'listo' | 'error';

function normalizar(texto: string): string {
  return texto
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase('es');
}

export function Pacientes() {
  const [texto, setTexto] = useState('');
  const [filtro, setFiltro] = useState<Filtro>('TODAS');
  const [filas, setFilas] = useState<PacienteResumen[]>([]);
  const [estado, setEstado] = useState<Estado>('cargando');
  const [error, setError] = useState('');
  const [intento, setIntento] = useState(0);
  const [pagina, setPagina] = useState(1);

  useEffect(() => {
    const controlador = new AbortController();
    let activo = true;

    async function cargar() {
      setEstado('cargando');
      setError('');

      try {
        const consulta = texto.trim();
        let datos: PacienteResumen[];

        if (filtro === 'TODAS') {
          datos =
            consulta.length > 0
              ? await buscarPacientes(consulta, {
                  signal: controlador.signal,
                })
              : await listarPacientes({
                  limite: MAX_PACIENTES,
                  signal: controlador.signal,
                });
        } else {
          const base = await listarPacientesPorAtencion(filtro, {
            signal: controlador.signal,
          });
          const buscado = normalizar(consulta);
          datos =
            buscado.length > 0
              ? base.filter((paciente) =>
                  normalizar(paciente.nombre).includes(buscado),
                )
              : base;
        }

        if (activo) {
          setFilas(datos);
          setEstado('listo');
        }
      } catch (fallo) {
        if (!activo || controlador.signal.aborted) {
          return;
        }

        setError(mensajeDeError(fallo));
        setEstado('error');
      }
    }

    const temporizador = window.setTimeout(
      () => void cargar(),
      texto.trim() ? RETRASO_BUSQUEDA_MS : 0,
    );

    return () => {
      activo = false;
      controlador.abort();
      window.clearTimeout(temporizador);
    };
  }, [texto, filtro, intento]);

  const cantidadPaginas = Math.ceil(filas.length / TAMANIO_PAGINA_PACIENTES);
  const paginaVisible = Math.min(pagina, Math.max(cantidadPaginas, 1));
  const indiceInicio = (paginaVisible - 1) * TAMANIO_PAGINA_PACIENTES;
  const filasVisibles = filas.slice(
    indiceInicio,
    indiceInicio + TAMANIO_PAGINA_PACIENTES,
  );

  return (
    <section className={estilos.pagina} aria-labelledby="titulo-historia">
      <header className={estilos.cabecera}>
        <div className={estilos.introduccion}>
          <p className={estilos.antetitulo}>Ficha completa</p>
          <h1 className={estilos.titulo} id="titulo-historia">
            Historia clínica
          </h1>
          <p className={estilos.subtitulo}>
            Consultas, vacunas, cirugías y tratamientos de cada mascota.
          </p>
        </div>
      </header>

      <section className={estilos.panel} aria-label="Buscar mascota">
        <label className={estilos.campoAncho} htmlFor="buscar-mascota">
          Buscar mascota
          <input
            id="buscar-mascota"
            onChange={(evento) => {
              setTexto(evento.target.value);
              setPagina(1);
            }}
            placeholder="Nombre de la mascota"
            type="search"
            value={texto}
          />
        </label>

        <div
          className={estilos.chips}
          aria-label="Filtrar mascotas por tipo de atención"
          role="group"
        >
          {CATEGORIAS.map((categoria) => {
            const activo = filtro === categoria.id;

            return (
              <button
                aria-pressed={activo}
                className={`${estilos.chip} ${activo ? estilos.chipActivo : ''}`}
                key={categoria.id}
                onClick={() => {
                  setFiltro(categoria.id);
                  setPagina(1);
                }}
                type="button"
              >
                {categoria.etiqueta}
              </button>
            );
          })}
        </div>

        {estado === 'cargando' ? (
          <p className={estilos.cargando}>Cargando mascotas…</p>
        ) : estado === 'error' ? (
          <Alerta
            acciones={
              <Boton
                onClick={() => setIntento((actual) => actual + 1)}
                variante="secundario"
              >
                Reintentar
              </Boton>
            }
            role="alert"
            tono="error"
          >
            {error}
          </Alerta>
        ) : filas.length === 0 ? (
          <p className={estilos.vacio}>
            {filtro !== 'TODAS'
              ? 'No hay mascotas con atenciones de esta categoría.'
              : texto.trim()
                ? 'No encontramos mascotas con ese nombre.'
                : 'Todavía no hay mascotas en el padrón.'}
          </p>
        ) : (
          <>
            <ul className={estilos.lista}>
              {filasVisibles.map((paciente) => (
                <li key={paciente.id}>
                  <Link
                    className={`${estilos.tarjeta} ${estilos.enlace}`}
                    to={`/historia-clinica/${paciente.id}`}
                  >
                    <span className={estilos.tarjetaTitulo}>
                      {paciente.nombre}
                    </span>
                    <span className={estilos.meta}>
                      <span>{paciente.especie_nombre}</span>
                      {paciente.raza_nombre ? (
                        <span>{paciente.raza_nombre}</span>
                      ) : null}
                      <DuenioMascota pacienteId={paciente.id} />
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
            <Paginacion
              ariaLabel="Paginación de mascotas"
              cantidadPaginas={cantidadPaginas}
              onCambiarPagina={setPagina}
              pagina={paginaVisible}
            />
          </>
        )}
      </section>
    </section>
  );
}
