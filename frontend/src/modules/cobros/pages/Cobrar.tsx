import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { Alerta } from '../../../core/components/ui/Alerta';
import { Boton } from '../../../core/components/ui/Boton';
import { buscarPersonas, mensajeDeError } from '../api';
import { usePuedeVerDeudores } from '../permisos';
import type { PersonaBusqueda } from '../tipos';
import estilos from '../cobros.module.css';

/** Retraso corto para no saturar la API mientras se escribe. */
const RETRASO_BUSQUEDA_MS = 250;
const TAMANIO_PAGINA = 5;

type Estado = 'cargando' | 'listo' | 'error';

type Consulta = {
  clave: string;
  estado: Estado;
  filas: PersonaBusqueda[];
  error: string;
  hayMas: boolean;
};

/** Pantalla de entrada de cobros: buscar el cliente y abrir su cuenta. */
export function Cobrar() {
  const [texto, setTexto] = useState('');
  const [pagina, setPagina] = useState(0);
  const [reintento, setReintento] = useState(0);
  const [consultaAplicada, setConsultaAplicada] = useState<Consulta | null>(null);
  const puedeVerDeudores = usePuedeVerDeudores();

  const consulta = texto.trim();
  const clave = `${consulta}:${pagina}`;
  const vigente = consultaAplicada?.clave === clave ? consultaAplicada : null;
  const estado: Estado = vigente?.estado ?? 'cargando';
  const resultados = vigente?.filas ?? [];
  const error = vigente?.error ?? '';
  const hayMas = vigente?.hayMas ?? false;

  useEffect(() => {
    const busqueda = texto.trim();
    const control = new AbortController();
    const temporizador = window.setTimeout(async () => {
      setConsultaAplicada({
        clave: `${busqueda}:${pagina}`,
        estado: 'cargando',
        filas: [],
        error: '',
        hayMas: false,
      });

      try {
        const personas = await buscarPersonas(busqueda, {
          limite: TAMANIO_PAGINA + 1,
          offset: pagina * TAMANIO_PAGINA,
          signal: control.signal,
        });

        if (control.signal.aborted) {
          return;
        }

        setConsultaAplicada({
          clave: `${busqueda}:${pagina}`,
          estado: 'listo',
          filas: personas.slice(0, TAMANIO_PAGINA),
          error: '',
          hayMas: personas.length > TAMANIO_PAGINA,
        });
      } catch (fallo) {
        if (control.signal.aborted) {
          return;
        }

        setConsultaAplicada({
          clave: `${busqueda}:${pagina}`,
          estado: 'error',
          filas: [],
          error: mensajeDeError(fallo),
          hayMas: false,
        });
      }
    }, RETRASO_BUSQUEDA_MS);

    return () => {
      window.clearTimeout(temporizador);
      control.abort();
    };
  }, [texto, pagina, reintento]);

  return (
    <section className={estilos.pagina} aria-labelledby="titulo-cobros">
      <div className={`${estilos.cabecera} ${estilos.cabeceraCobros}`}>
        <div>
          <p className={estilos.antetitulo}>Gestión de cobros</p>
          <h1 className={estilos.titulo} id="titulo-cobros">
            Cobros
          </h1>
          <p className={estilos.subtitulo}>
            Buscá al cliente para cobrar, registrar una seña o ver su saldo.
          </p>
        </div>

        {puedeVerDeudores ? (
          <div className={estilos.acciones}>
            <Link className={estilos.botonEnlaceSecundario} to="/cobros/deudores">
              Ver deudores
            </Link>
          </div>
        ) : null}
      </div>

      <div className={estilos.busquedaPanel}>
        <div className={estilos.busquedaEncabezado}>
          <span className={estilos.busquedaIcono} aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none">
              <circle cx="10.8" cy="10.8" r="6.3" />
              <path d="m15.5 15.5 4.2 4.2" />
            </svg>
          </span>
          <div>
            <h2>Encontrá una cuenta</h2>
            <p>Buscá por nombre, DNI o teléfono.</p>
          </div>
        </div>
        <label className="sr-only" htmlFor="cobros-busqueda">
          Buscar cliente
        </label>
        <div>
          <input
            autoComplete="off"
            aria-label="Buscar cliente"
            id="cobros-busqueda"
            onChange={(evento) => {
              setTexto(evento.target.value);
              setPagina(0);
            }}
            placeholder="Ej.: Ana, 30111222, 1144556677"
            type="search"
            value={texto}
          />
        </div>
      </div>

      {estado === 'cargando' ? (
        <p className={estilos.cargando} role="status">
          {consulta ? 'Buscando clientes…' : 'Cargando clientes…'}
        </p>
      ) : null}

      {estado === 'error' ? (
        <Alerta
          acciones={
            <Boton
              onClick={() => setReintento((valor) => valor + 1)}
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
      ) : null}

      {estado === 'listo' && resultados.length === 0 ? (
        <p className={estilos.vacio}>
          {pagina > 0
            ? 'No hay más clientes en esta página.'
            : consulta
            ? 'No encontramos clientes con ese dato.'
            : 'No hay clientes registrados todavía.'}
        </p>
      ) : null}

      {estado === 'listo' && resultados.length > 0 ? (
        <>
          <section className={estilos.listadoClientes} aria-labelledby="titulo-clientes-cobros">
            <div className={estilos.encabezadoClientes}>
              <div>
                {consulta ? (
                  <p className={estilos.antetitulo}>Resultados de búsqueda</p>
                ) : null}
                <h2 className={estilos.tituloSeccion} id="titulo-clientes-cobros">
                  {consulta ? 'Clientes encontrados' : 'Clientes'}
                </h2>
              </div>
              <span className={estilos.rangoResultados}>
                {pagina * TAMANIO_PAGINA + 1}–
                {pagina * TAMANIO_PAGINA + resultados.length}
              </span>
            </div>
            <ul className={estilos.resultados}>
              {resultados.map((persona) => (
                <li key={persona.id}>
                  <Link className={estilos.resultado} to={`/cobros/cliente/${persona.id}`}>
                    <span className={estilos.avatarCliente} aria-hidden="true">
                      {persona.nombre.charAt(0)}{persona.apellido.charAt(0)}
                    </span>
                    <span className={estilos.resultadoContenido}>
                      <span className={estilos.filaResultado}>
                        <strong className={estilos.resultadoNombre}>
                          {persona.apellido}, {persona.nombre}
                        </strong>
                        {persona.dni_pendiente ? (
                          <span className={`${estilos.insignia} ${estilos.insigniaAviso}`}>
                            DNI pendiente
                          </span>
                        ) : null}
                      </span>
                      <span className={estilos.textoSuave}>
                        {persona.dni ? `DNI ${persona.dni}` : 'Sin DNI registrado'}
                        {persona.telefonos.length > 0
                          ? ` · Tel. ${persona.telefonos.join(' · ')}`
                          : ''}
                      </span>
                    </span>
                    <span className={estilos.resultadoAccion}>
                      Ver cuenta y cobrar
                      <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                        <path d="m9 18 6-6-6-6" />
                      </svg>
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        </>
      ) : null}

      {estado === 'listo' && (resultados.length > 0 || pagina > 0) ? (
        <nav className={estilos.paginacion} aria-label="Paginación de clientes">
          <button
            className={estilos.botonPaginacion}
            disabled={pagina === 0}
            onClick={() => setPagina((actual) => Math.max(0, actual - 1))}
            type="button"
          >
            Anterior
          </button>
          <span className={estilos.estadoPaginacion}>Página {pagina + 1}</span>
          <button
            className={estilos.botonPaginacion}
            disabled={!hayMas}
            onClick={() => setPagina((actual) => actual + 1)}
            type="button"
          >
            Siguiente
          </button>
        </nav>
      ) : null}

    </section>
  );
}
