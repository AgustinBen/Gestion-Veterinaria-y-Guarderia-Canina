import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { Alerta } from '../../../core/components/ui/Alerta';
import { Boton } from '../../../core/components/ui/Boton';
import { Paginacion } from '../../../core/components/ui/Paginacion';
import { formatearDinero } from '../../../core/formatos/dinero';
import { listarDeudores, mensajeDeError } from '../api';
import type { Deudor, OrdenDeudores } from '../tipos';
import estilos from '../cobros.module.css';

type Estado = 'cargando' | 'listo' | 'error';

type Carga = {
  clave: string;
  estado: Estado;
  filas: Deudor[];
  error: string;
};

/** "2026-03-05" → "05/03/2026" sin pasar por zonas horarias. */
function formatearFecha(fecha: string): string {
  const coincidencia = /^(\d{4})-(\d{2})-(\d{2})/.exec(fecha);

  return coincidencia
    ? `${coincidencia[3]}/${coincidencia[2]}/${coincidencia[1]}`
    : fecha;
}

const ORDENES: readonly { id: OrdenDeudores; etiqueta: string }[] = [
  { id: 'monto', etiqueta: 'Por monto' },
  { id: 'antiguedad', etiqueta: 'Por antigüedad' },
];

/** El backend acepta hasta 100 deudores por pedido. */
const LIMITE_BACKEND = 100;
const TAMANIO_PAGINA_DEUDORES = 5;

/** Listado de clientes con deuda. La deuda solo avisa: nunca bloquea (RN-23). */
export function Deudores() {
  const [orden, setOrden] = useState<OrdenDeudores>('monto');
  const [intento, setIntento] = useState(0);
  const [pagina, setPagina] = useState(1);
  const clave = `${orden}:${intento}`;
  const [carga, setCarga] = useState<Carga>({
    clave,
    estado: 'cargando',
    filas: [],
    error: '',
  });

  useEffect(() => {
    const control = new AbortController();
    let activo = true;
    const claveConsulta = `${orden}:${intento}`;

    async function cargar() {
      try {
        const filas: Deudor[] = [];
        let offset = 0;

        // Se traen todas las páginas del backend para paginar de a cinco con
        // el mismo paginado que el resto de los listados.
        for (;;) {
          const tramo = await listarDeudores({
            orden,
            limite: LIMITE_BACKEND,
            offset,
            signal: control.signal,
          });
          filas.push(...tramo);

          if (tramo.length < LIMITE_BACKEND) {
            break;
          }

          offset += tramo.length;
        }

        if (!activo || control.signal.aborted) {
          return;
        }

        setCarga({ clave: claveConsulta, estado: 'listo', filas, error: '' });
      } catch (fallo) {
        if (!activo || control.signal.aborted) {
          return;
        }

        setCarga({
          clave: claveConsulta,
          estado: 'error',
          filas: [],
          error: mensajeDeError(fallo),
        });
      }
    }

    void cargar();

    return () => {
      activo = false;
      control.abort();
    };
  }, [orden, intento]);

  const vigente = carga.clave === clave ? carga : null;
  const estado: Estado = vigente?.estado ?? 'cargando';
  const filas = vigente?.filas ?? [];
  const error = vigente?.error ?? '';
  const cantidadPaginas = Math.ceil(filas.length / TAMANIO_PAGINA_DEUDORES);
  const paginaVisible = Math.min(pagina, Math.max(cantidadPaginas, 1));
  const indiceInicio = (paginaVisible - 1) * TAMANIO_PAGINA_DEUDORES;
  const deudores = filas.slice(
    indiceInicio,
    indiceInicio + TAMANIO_PAGINA_DEUDORES,
  );

  return (
    <section className={estilos.pagina} aria-labelledby="titulo-deudores">
      <div className={`${estilos.cabecera} ${estilos.cabeceraDeudores}`}>
        <div className={estilos.introduccionDeudores}>
          <p className={estilos.antetitulo}>Cuentas por cobrar</p>
          <h1 className={estilos.titulo} id="titulo-deudores">
            Deudores
          </h1>
          <p className={estilos.subtitulo}>
            Clientes con saldo pendiente. La deuda se calcula sola y nunca
            bloquea un servicio.
          </p>
        </div>

        <div className={estilos.acciones}>
          <Link className={estilos.botonEnlaceSecundario} to="/cobros">
            Volver a Cobros
            <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M19 12H5m7 7-7-7 7-7" />
            </svg>
          </Link>
        </div>
      </div>

      <div className={estilos.barOrden}>
        <div>
          <span className={estilos.barOrdenTitulo}>Priorizar seguimiento</span>
          <span className={estilos.barOrdenTexto}>
            Elegí cómo ordenar los saldos pendientes.
          </span>
        </div>
        <div className={estilos.selector} role="group" aria-label="Ordenar deudores">
          {ORDENES.map((opcion) => (
            <button
              aria-pressed={orden === opcion.id}
              className={[
                estilos.selectorBoton,
                orden === opcion.id ? estilos.selectorActivo : '',
              ]
                .filter(Boolean)
                .join(' ')}
              key={opcion.id}
              onClick={() => {
                setOrden(opcion.id);
                setPagina(1);
              }}
              type="button"
            >
              {opcion.etiqueta}
            </button>
          ))}
        </div>
      </div>

      {estado === 'cargando' ? (
        <p className={estilos.cargando} role="status">
          Cargando deudores…
        </p>
      ) : null}

      {estado === 'error' ? (
        <Alerta
          acciones={
            <Boton
              onClick={() => setIntento((valor) => valor + 1)}
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

      {estado === 'listo' && deudores.length === 0 ? (
        <p className={estilos.vacio}>No hay clientes con deuda pendiente.</p>
      ) : null}

      {deudores.length > 0 ? (
        <>
          <div className={estilos.tablaPanel}>
            <div className={estilos.tablaEncabezado}>
              <div>
                <h2 className={estilos.tituloSeccion}>Saldos pendientes</h2>
                <p className={estilos.textoSuave}>
                  Consultá el detalle de cargos y pagos de cada cliente.
                </p>
              </div>
              <span className={estilos.etiquetaPendiente}>
                <span
                  aria-hidden="true"
                  className={estilos.puntoPendiente}
                />
                Pendiente
              </span>
            </div>
            <div className={estilos.tablaMarco}>
              <table className={estilos.tabla}>
                <caption className="sr-only">Clientes con deuda pendiente</caption>
                <thead>
                  <tr>
                    <th scope="col">Cliente</th>
                    <th scope="col" className={estilos.numero}>
                      Saldo
                    </th>
                    <th scope="col" className={estilos.numero}>
                      Cargos
                    </th>
                    <th scope="col" className={estilos.numero}>
                      Deuda más antigua
                    </th>
                    <th scope="col" className={estilos.numero}>
                      Acciones
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {deudores.map((deudor) => (
                    <tr key={deudor.persona.id}>
                      <td data-etiqueta="Cliente">
                        <span className={estilos.deudorCliente}>
                          <span className={estilos.avatarCliente} aria-hidden="true">
                            {deudor.persona.nombre.charAt(0)}
                            {deudor.persona.apellido.charAt(0)}
                          </span>
                          <span className={estilos.concepto}>
                            <span className={estilos.filaResultado}>
                              <strong>
                                {deudor.persona.apellido}, {deudor.persona.nombre}
                              </strong>
                              {deudor.saldo_migracion_centavos > 0 ? (
                                <span
                                  className={`${estilos.insignia} ${estilos.insigniaAviso}`}
                                >
                                  Deuda migrada
                                </span>
                              ) : null}
                            </span>
                            <span className={estilos.textoSuave}>
                              {deudor.persona.telefono_principal
                                ? `Tel. ${deudor.persona.telefono_principal}`
                                : 'Sin teléfono registrado'}
                            </span>
                          </span>
                        </span>
                      </td>
                      <td
                        className={`${estilos.numero} ${estilos.saldoDeudor}`}
                        data-etiqueta="Saldo"
                      >
                        <strong>{formatearDinero(deudor.saldo_total_centavos)}</strong>
                      </td>
                      <td className={estilos.numero} data-etiqueta="Cargos">
                        {deudor.cantidad_cargos_pendientes}
                      </td>
                      <td className={estilos.numero} data-etiqueta="Deuda más antigua">
                        {formatearFecha(deudor.deuda_mas_antigua)}
                      </td>
                      <td className={estilos.numero} data-etiqueta="Acciones">
                        <Link
                          className={estilos.accionCuenta}
                          to={`/cobros/cliente/${deudor.persona.id}`}
                        >
                          Ver cuenta de {deudor.persona.apellido},{' '}
                          {deudor.persona.nombre}
                          <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                            <path d="m9 18 6-6-6-6" />
                          </svg>
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <Paginacion
            ariaLabel="Paginación de deudores"
            cantidadPaginas={cantidadPaginas}
            onCambiarPagina={setPagina}
            pagina={paginaVisible}
          />
        </>
      ) : null}
    </section>
  );
}
