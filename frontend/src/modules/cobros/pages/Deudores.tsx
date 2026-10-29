import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';

import { Alerta } from '../../../core/components/ui/Alerta';
import { Boton } from '../../../core/components/ui/Boton';
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
  hayMas: boolean;
  cargandoMas: boolean;
  errorCargarMas: string;
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

const LIMITE_POR_PAGINA = 100;

/** Listado de clientes con deuda. La deuda solo avisa: nunca bloquea (RN-23). */
export function Deudores() {
  const [orden, setOrden] = useState<OrdenDeudores>('monto');
  const [intento, setIntento] = useState(0);
  const cargandoMasRef = useRef(false);
  const clave = `${orden}:${intento}`;
  const [carga, setCarga] = useState<Carga>({
    clave,
    estado: 'cargando',
    filas: [],
    error: '',
    hayMas: false,
    cargandoMas: false,
    errorCargarMas: '',
  });

  useEffect(() => {
    const control = new AbortController();
    let activo = true;
    const claveConsulta = `${orden}:${intento}`;

    listarDeudores({
      orden,
      limite: LIMITE_POR_PAGINA,
      offset: 0,
      signal: control.signal,
    })
      .then((filas) => {
        if (!activo || control.signal.aborted) {
          return;
        }

        setCarga({
          clave: claveConsulta,
          estado: 'listo',
          filas,
          error: '',
          hayMas: filas.length === LIMITE_POR_PAGINA,
          cargandoMas: false,
          errorCargarMas: '',
        });
      })
      .catch((fallo) => {
        if (!activo || control.signal.aborted) {
          return;
        }

        setCarga({
          clave: claveConsulta,
          estado: 'error',
          filas: [],
          error: mensajeDeError(fallo),
          hayMas: false,
          cargandoMas: false,
          errorCargarMas: '',
        });
      });

    return () => {
      activo = false;
      control.abort();
    };
  }, [orden, intento]);

  const vigente = carga.clave === clave ? carga : null;
  const estado: Estado = vigente?.estado ?? 'cargando';
  const deudores = vigente?.filas ?? [];
  const error = vigente?.error ?? '';
  const hayMas = vigente?.hayMas ?? false;
  const cargandoMas = vigente?.cargandoMas ?? false;
  const errorCargarMas = vigente?.errorCargarMas ?? '';

  async function cargarMas() {
    if (cargandoMasRef.current || !vigente || !hayMas) {
      return;
    }

    cargandoMasRef.current = true;
    setCarga((actual) =>
      actual.clave === clave
        ? { ...actual, cargandoMas: true, errorCargarMas: '' }
        : actual,
    );

    try {
      const siguientes = await listarDeudores({
        orden,
        limite: LIMITE_POR_PAGINA,
        offset: deudores.length,
      });

      setCarga((actual) =>
        actual.clave === clave
          ? {
              ...actual,
              filas: [...actual.filas, ...siguientes],
              hayMas: siguientes.length === LIMITE_POR_PAGINA,
              cargandoMas: false,
              errorCargarMas: '',
            }
          : actual,
      );
    } catch (fallo) {
      setCarga((actual) =>
        actual.clave === clave
          ? {
              ...actual,
              cargandoMas: false,
              errorCargarMas: mensajeDeError(fallo),
            }
          : actual,
      );
    } finally {
      cargandoMasRef.current = false;
    }
  }

  return (
    <section className={estilos.pagina} aria-labelledby="titulo-deudores">
      <div className={estilos.cabecera}>
        <div>
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
          </Link>
        </div>
      </div>

      <div className={estilos.acciones}>
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
              onClick={() => setOrden(opcion.id)}
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
                    </td>
                    <td className={estilos.numero} data-etiqueta="Saldo">
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
                        className={estilos.enlace}
                        to={`/cobros/cliente/${deudor.persona.id}`}
                      >
                        Ver cuenta de {deudor.persona.apellido},{' '}
                        {deudor.persona.nombre}
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {errorCargarMas ? (
            <Alerta
              acciones={
                <Boton
                  cargando={cargandoMas}
                  disabled={cargandoMas}
                  onClick={cargarMas}
                  variante="secundario"
                >
                  Reintentar carga
                </Boton>
              }
              role="alert"
              tono="error"
            >
              {errorCargarMas}
            </Alerta>
          ) : null}

          {hayMas && !errorCargarMas ? (
            <Boton
              cargando={cargandoMas}
              disabled={cargandoMas}
              onClick={cargarMas}
              variante="secundario"
            >
              Cargar más deudores
            </Boton>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
