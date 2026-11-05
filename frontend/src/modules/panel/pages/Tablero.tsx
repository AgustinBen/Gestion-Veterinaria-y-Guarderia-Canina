import { useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';

import { Alerta } from '../../../core/components/ui/Alerta';
import { Boton } from '../../../core/components/ui/Boton';
import { formatearDinero } from '../../../core/formatos/dinero';
import {
  listarResumen,
  listarIngresos,
  mensajeDeError,
  obtenerDeudas,
} from '../api';
import { Filtros } from '../components/Filtros';
import { leerFiltros, parametrosDeFiltros } from '../components/filtrosPanel';
import { TarjetaMetrica } from '../components/TarjetaMetrica';
import type {
  DeudasPanel,
  FiltrosPanel,
  IngresoHistorial,
  ResumenPanel,
} from '../tipos';
import estilos from '../panel.module.css';

type DatosPanel = {
  resumen: ResumenPanel;
  deudas: DeudasPanel;
};

type EstadoCarga =
  | { estado: 'cargando' }
  | { estado: 'error'; error: string }
  | { estado: 'listo'; datos: DatosPanel };

type EstadoHistorial =
  | { estado: 'cargando' }
  | { estado: 'error'; error: string }
  | { estado: 'listo'; ingresos: IngresoHistorial[] };

/** Tablero financiero del Dueño (T-50, RN-40). */
export function Tablero() {
  const [params, setParams] = useSearchParams();
  const filtros = leerFiltros(params);
  const { periodo, desde, hasta } = filtros;
  const [reintento, setReintento] = useState(0);
  const [carga, setCarga] = useState<EstadoCarga>({ estado: 'cargando' });
  const [historialAbierto, setHistorialAbierto] = useState(false);
  const [historial, setHistorial] = useState<EstadoHistorial>({
    estado: 'cargando',
  });
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const control = new AbortController();

    Promise.all([
      listarResumen(filtros, { signal: control.signal }),
      obtenerDeudas({ signal: control.signal }),
    ])
      .then(([resumen, deudas]) => {
        if (control.signal.aborted) {
          return;
        }

        setCarga({
          estado: 'listo',
          datos: { resumen, deudas },
        });
      })
      .catch((fallo) => {
        if (control.signal.aborted) {
          return;
        }

        setCarga({ estado: 'error', error: mensajeDeError(fallo) });
      });

    return () => control.abort();
    // La consulta se dispara cuando cambia el período elegido.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtros.periodo, filtros.desde, filtros.hasta, reintento]);

  useEffect(() => {
    if (!historialAbierto) {
      return;
    }

    const control = new AbortController();
    listarIngresos({ periodo, desde, hasta }, { signal: control.signal })
      .then((ingresos) => {
        if (!control.signal.aborted) {
          setHistorial({ estado: 'listo', ingresos });
        }
      })
      .catch((fallo) => {
        if (!control.signal.aborted) {
          setHistorial({ estado: 'error', error: mensajeDeError(fallo) });
        }
      });

    return () => control.abort();
  }, [desde, hasta, periodo, historialAbierto]);

  useEffect(() => {
    if (!historialAbierto) {
      return;
    }

    modalRef.current?.focus();
    const cerrarConEscape = (evento: KeyboardEvent) => {
      if (evento.key === 'Escape') {
        setHistorialAbierto(false);
      }
    };
    document.addEventListener('keydown', cerrarConEscape);
    return () => document.removeEventListener('keydown', cerrarConEscape);
  }, [historialAbierto]);

  function cambiarFiltros(nuevos: FiltrosPanel) {
    setParams(parametrosDeFiltros(nuevos));
  }

  return (
    <section aria-labelledby="titulo-panel" className={estilos.pagina}>
      <div className={`${estilos.cabecera} ${estilos.cabeceraCobros}`}>
        <div>
          <p className={estilos.antetitulo}>Panel financiero</p>
          <h1 className={estilos.titulo} id="titulo-panel">
            Panel
          </h1>
          <p className={estilos.subtitulo}>
            Ingresos, egresos, rentabilidad y deudas del negocio.
          </p>
        </div>
        <nav aria-label="Secciones del panel" className={estilos.navegacion}>
          <Boton
            className={estilos.botonNavegacion}
            onClick={() => {
              setHistorial({ estado: 'cargando' });
              setHistorialAbierto(true);
            }}
            variante="secundario"
          >
            Ingresos
          </Boton>
          <Link to="/panel/egresos">Egresos</Link>
          <Link to="/panel/gastos-externos">Gastos a externos</Link>
          <Link to="/panel/categorias">Categorías</Link>
        </nav>
      </div>

      <Filtros filtros={filtros} onCambiar={cambiarFiltros} />

      {carga.estado === 'cargando' ? (
        <p role="status">Cargando panel…</p>
      ) : null}

      {carga.estado === 'error' ? (
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
          {carga.error}
        </Alerta>
      ) : null}

      {carga.estado === 'listo' ? (
        <>
          <div className={estilos.metricas}>
            <TarjetaMetrica
              titulo="Ingresos"
              valor={carga.datos.resumen.ingresos_centavos}
            />
            <TarjetaMetrica
              titulo="Egresos operativos"
              valor={carga.datos.resumen.egresos_operativos_centavos}
            />
            <TarjetaMetrica
              titulo="Gastos a externos"
              valor={carga.datos.resumen.gastos_externos_centavos}
            />
            <TarjetaMetrica
              destacada
              motivo={carga.datos.resumen.rentabilidad_neta_motivo}
              titulo="Rentabilidad neta"
              valor={carga.datos.resumen.rentabilidad_neta_centavos}
            />
          </div>

          <section
            aria-label="Deudas pendientes"
            className={estilos.tarjetaDeudas}
          >
            <h2>Deudas pendientes</h2>
            <p className={estilos.tarjetaValor}>
              {formatearDinero(carga.datos.deudas.total_adeudado_centavos)}
            </p>
            <p className={estilos.textoSuave}>
              {carga.datos.deudas.cantidad_clientes === 0
                ? 'No hay deudas pendientes.'
                : `${carga.datos.deudas.cantidad_clientes} cliente(s) con deuda. El saldo adeudado no se descuenta de la rentabilidad.`}
            </p>
            <Link className={estilos.enlace} to="/cobros/deudores">
              Ver deudores
            </Link>
          </section>

          {historialAbierto ? (
            <div
              aria-labelledby="titulo-historial-ingresos"
              aria-modal="true"
              className={estilos.modalFondo}
              onMouseDown={(evento) => {
                if (evento.target === evento.currentTarget) {
                  setHistorialAbierto(false);
                }
              }}
              ref={modalRef}
              role="dialog"
              tabIndex={-1}
            >
              <div className={estilos.modal}>
                <header className={estilos.modalCabecera}>
                  <div>
                    <h2
                      className={estilos.modalTitulo}
                      id="titulo-historial-ingresos"
                    >
                      Historial de ingresos
                    </h2>
                    <p>
                      Ingresos del período seleccionado, incluidos los reversos.
                    </p>
                  </div>
                  <button
                    aria-label="Cerrar"
                    className={estilos.modalCerrar}
                    onClick={() => setHistorialAbierto(false)}
                    type="button"
                  >
                    ×
                  </button>
                </header>
                <div className={estilos.modalCuerpo}>
                  {historial.estado === 'cargando' ? (
                    <p role="status">Cargando historial de ingresos…</p>
                  ) : null}
                  {historial.estado === 'error' ? (
                    <Alerta role="alert" tono="error">
                      {historial.error}
                    </Alerta>
                  ) : null}
                  {historial.estado === 'listo' &&
                  historial.ingresos.length === 0 ? (
                    <p className={estilos.textoSuave}>
                      No hay ingresos para el período.
                    </p>
                  ) : null}
                  {historial.estado === 'listo' &&
                  historial.ingresos.length > 0 ? (
                    <div className={estilos.tablaContenedor}>
                      <table className={estilos.tabla}>
                        <caption>Ingresos del período</caption>
                        <thead>
                          <tr>
                            <th scope="col">Fecha</th>
                            <th scope="col">Servicio</th>
                            <th scope="col">Medio</th>
                            <th scope="col">Monto</th>
                            <th scope="col">Estado</th>
                          </tr>
                        </thead>
                        <tbody>
                          {historial.ingresos.map((ingreso) => (
                            <tr key={ingreso.id}>
                              <td>{ingreso.fecha}</td>
                              <td>{ingreso.tipo_servicio}</td>
                              <td>{ingreso.medio}</td>
                              <td>{formatearDinero(ingreso.monto_centavos)}</td>
                              <td>{ingreso.estado}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : null}
                </div>
              </div>
            </div>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
