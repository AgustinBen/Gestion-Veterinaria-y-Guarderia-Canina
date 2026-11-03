import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { Alerta } from '../../../core/components/ui/Alerta';
import { Boton } from '../../../core/components/ui/Boton';
import { formatearDinero } from '../../../core/formatos/dinero';
import { mensajeDeError, obtenerDetalleCliente } from '../api';
import type { DetalleCliente as Detalle } from '../tipos';
import estilos from '../panel.module.css';

type Resultado =
  | { clave: string; estado: 'error'; error: string }
  | { clave: string; estado: 'listo'; detalle: Detalle };

/** Servicios de un cliente con total, pagado, saldo y ajustes (T-50). */
export function DetalleCliente() {
  const { personaId } = useParams<{ personaId: string }>();
  const id = Number(personaId);
  const idValido = Number.isInteger(id) && id > 0;
  const [reintento, setReintento] = useState(0);
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const clave = `${personaId}-${reintento}`;
  const cargando = idValido && resultado?.clave !== clave;

  useEffect(() => {
    if (!idValido) {
      return;
    }

    const control = new AbortController();

    obtenerDetalleCliente(id, { signal: control.signal })
      .then((detalle) => {
        if (!control.signal.aborted) {
          setResultado({ clave, estado: 'listo', detalle });
        }
      })
      .catch((fallo) => {
        if (!control.signal.aborted) {
          setResultado({ clave, estado: 'error', error: mensajeDeError(fallo) });
        }
      });

    return () => control.abort();
  }, [clave, id, idValido]);

  return (
    <div className={estilos.pagina}>
      <div className={`${estilos.cabecera} ${estilos.cabeceraCobros}`}>
        <div>
          <p className={estilos.antetitulo}>Panel financiero</p>
          <h1 className={estilos.titulo}>Detalle por cliente</h1>
          <p className={estilos.subtitulo}>
            Servicios, pagos y saldo del cliente.
          </p>
          <Link className={`${estilos.enlace} ${estilos.volver}`} to="/panel">
            Volver al panel
          </Link>
        </div>
      </div>

      {!idValido ? (
        <Alerta role="alert" tono="error">
          Cliente inválido.
        </Alerta>
      ) : null}

      {cargando ? <p role="status">Cargando servicios del cliente…</p> : null}

      {idValido && resultado?.clave === clave && resultado.estado === 'error' ? (
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
          {resultado.error}
        </Alerta>
      ) : null}

      {idValido && resultado?.clave === clave && resultado.estado === 'listo' ? (
        <>
          <h2>
            {resultado.detalle.apellido}, {resultado.detalle.nombre}
          </h2>

          {resultado.detalle.servicios.length === 0 ? (
            <p className={estilos.textoSuave}>
              Este cliente no tiene servicios registrados.
            </p>
          ) : (
            <div className={estilos.tablaContenedor}>
              <table className={estilos.tabla}>
                <caption>Servicios del cliente</caption>
                <thead>
                  <tr>
                    <th scope="col">Tipo</th>
                    <th scope="col">Concepto</th>
                    <th scope="col">Total</th>
                    <th scope="col">Pagado</th>
                    <th scope="col">Saldo</th>
                    <th scope="col">Ajustes</th>
                  </tr>
                </thead>
                <tbody>
                  {resultado.detalle.servicios.map((servicio) => (
                    <tr key={servicio.cargo_id}>
                      <td>{servicio.tipo_servicio}</td>
                      <td>{servicio.concepto}</td>
                      <td>{formatearDinero(servicio.total_centavos)}</td>
                      <td>{formatearDinero(servicio.pagado_centavos)}</td>
                      <td>{formatearDinero(servicio.saldo_centavos)}</td>
                      <td>{servicio.ajustes}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      ) : null}
    </div>
  );
}
