import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';

import { Alerta } from '../../../core/components/ui/Alerta';
import { Boton } from '../../../core/components/ui/Boton';
import { formatearDinero } from '../../../core/formatos/dinero';
import {
  listarIngresosPorMedio,
  listarResumen,
  mensajeDeError,
  obtenerDeudas,
} from '../api';
import { Filtros } from '../components/Filtros';
import { leerFiltros, parametrosDeFiltros } from '../components/filtrosPanel';
import { TarjetaMetrica } from '../components/TarjetaMetrica';
import type {
  DeudasPanel,
  FiltrosPanel,
  IngresoPorMedio,
  ResumenPanel,
} from '../tipos';
import estilos from '../panel.module.css';

type DatosPanel = {
  resumen: ResumenPanel;
  porMedio: IngresoPorMedio[];
  deudas: DeudasPanel;
};

type EstadoCarga =
  | { estado: 'cargando' }
  | { estado: 'error'; error: string }
  | { estado: 'listo'; datos: DatosPanel };

/** Tablero financiero del Dueño (T-50, RN-40). */
export function Tablero() {
  const [params, setParams] = useSearchParams();
  const filtros = leerFiltros(params);
  const [reintento, setReintento] = useState(0);
  const [carga, setCarga] = useState<EstadoCarga>({ estado: 'cargando' });

  useEffect(() => {
    const control = new AbortController();

    Promise.all([
      listarResumen(filtros, { signal: control.signal }),
      listarIngresosPorMedio(filtros, { signal: control.signal }),
      obtenerDeudas({ signal: control.signal }),
    ])
      .then(([resumen, porMedio, deudas]) => {
        if (control.signal.aborted) {
          return;
        }

        setCarga({
          estado: 'listo',
          datos: { resumen, porMedio, deudas },
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
        </>
      ) : null}
    </section>
  );
}
