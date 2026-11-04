import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';

import { Alerta } from '../../../core/components/ui/Alerta';
import { Boton } from '../../../core/components/ui/Boton';
import { Campo } from '../../../core/components/ui/Campo';
import { DialogoConfirmacion } from '../../../core/components/ui/DialogoConfirmacion';
import { formatearDinero, parsearDinero } from '../../../core/formatos/dinero';
import {
  anularGastoExterno,
  crearGastoExterno,
  generarIdempotencyKey,
  listarGastosExternos,
  mensajeDeError,
} from '../api';
import { calcularRango, fechaIsoLocal } from '../components/filtrosPanel';
import type { GastoExterno } from '../tipos';
import estilos from '../panel.module.css';

type Estado =
  | { estado: 'cargando' }
  | { estado: 'error'; error: string }
  | { estado: 'listo'; gastos: GastoExterno[] };

function rangoInicial(): { desde: string; hasta: string } {
  return calcularRango('mes');
}

/** Alta, listado y anulación de gastos a externos (T-22 / T-50). */
export function GastosExternos() {
  const [carga, setCarga] = useState<Estado>({ estado: 'cargando' });
  const [reintento, setReintento] = useState(0);
  const [rango, setRango] = useState(rangoInicial);
  const [descripcion, setDescripcion] = useState('');
  const [monto, setMonto] = useState('');
  const [fecha, setFecha] = useState(() => fechaIsoLocal(new Date()));
  const [errorAlta, setErrorAlta] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [aAnular, setAAnular] = useState<GastoExterno | null>(null);
  const [motivo, setMotivo] = useState('');
  const [errorAnular, setErrorAnular] = useState('');
  const [anulando, setAnulando] = useState(false);
  const enviandoRef = useRef(false);
  const anulandoRef = useRef(false);
  const [idempotencyKey, setIdempotencyKey] = useState(() =>
    generarIdempotencyKey(),
  );

  useEffect(() => {
    const control = new AbortController();

    listarGastosExternos(
      { desde: rango.desde, hasta: rango.hasta },
      { signal: control.signal },
    )
      .then((lista) => {
        if (!control.signal.aborted) {
          setCarga({ estado: 'listo', gastos: lista.items });
        }
      })
      .catch((fallo) => {
        if (!control.signal.aborted) {
          setCarga({ estado: 'error', error: mensajeDeError(fallo) });
        }
      });

    return () => control.abort();
  }, [rango.desde, rango.hasta, reintento]);

  async function registrar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();

    if (enviandoRef.current) {
      return;
    }

    let montoCentavos: number;

    try {
      montoCentavos = parsearDinero(monto);
    } catch (fallo) {
      setErrorAlta(fallo instanceof Error ? fallo.message : 'Monto inválido.');
      return;
    }

    if (!descripcion.trim()) {
      setErrorAlta('Escribí una descripción.');
      return;
    }

    enviandoRef.current = true;
    setEnviando(true);
    setErrorAlta('');

    try {
      await crearGastoExterno(
        {
          descripcion: descripcion.trim(),
          monto_centavos: montoCentavos,
          fecha,
        },
        { idempotencyKey },
      );
      setDescripcion('');
      setMonto('');
      setIdempotencyKey(generarIdempotencyKey());
      setReintento((valor) => valor + 1);
    } catch (fallo) {
      setErrorAlta(mensajeDeError(fallo));
    } finally {
      enviandoRef.current = false;
      setEnviando(false);
    }
  }

  async function confirmarAnulacion() {
    if (anulandoRef.current || aAnular === null) {
      return;
    }

    if (!motivo.trim()) {
      setErrorAnular('El motivo es obligatorio.');
      return;
    }

    anulandoRef.current = true;
    setAnulando(true);
    setErrorAnular('');

    try {
      await anularGastoExterno(aAnular.id, motivo.trim());
      setAAnular(null);
      setMotivo('');
      setReintento((valor) => valor + 1);
    } catch (fallo) {
      setErrorAnular(mensajeDeError(fallo));
    } finally {
      anulandoRef.current = false;
      setAnulando(false);
    }
  }

  return (
    <div className={estilos.pagina}>
      <div className={`${estilos.cabecera} ${estilos.cabeceraCobros}`}>
        <div>
          <p className={estilos.antetitulo}>Panel financiero</p>
          <h1 className={estilos.titulo}>Gastos a externos</h1>
          <p className={estilos.subtitulo}>
            Registrá honorarios y gastos de profesionales externos.
          </p>
          <Link className={`${estilos.enlace} ${estilos.volver}`} to="/panel">
            Volver al panel
          </Link>
        </div>
        <nav aria-label="Secciones del panel" className={estilos.navegacion}>
          <Link to="/panel/egresos">Egresos</Link>
          <Link to="/panel/categorias">Categorías</Link>
        </nav>
      </div>

      <section aria-label="Nuevo gasto a externo" className={estilos.tarjeta}>
        <h2>Registrar gasto a externo</h2>
        <form className={estilos.formulario} onSubmit={registrar}>
          <Campo etiqueta="Descripción" id="gasto-externo-descripcion" obligatorio>
            <input
              id="gasto-externo-descripcion"
              onChange={(evento) => setDescripcion(evento.target.value)}
              value={descripcion}
            />
          </Campo>

          <Campo etiqueta="Monto" id="gasto-externo-monto" obligatorio>
            <input
              id="gasto-externo-monto"
              inputMode="decimal"
              onChange={(evento) => setMonto(evento.target.value)}
              placeholder="10.000 o 10.000,50"
              value={monto}
            />
          </Campo>

          <Campo etiqueta="Fecha" id="gasto-externo-fecha" obligatorio>
            <input
              id="gasto-externo-fecha"
              onChange={(evento) => setFecha(evento.target.value)}
              type="date"
              value={fecha}
            />
          </Campo>

          {errorAlta ? (
            <Alerta role="alert" tono="error">
              {errorAlta}
            </Alerta>
          ) : null}

          <Boton cargando={enviando} type="submit">
            Registrar gasto
          </Boton>
        </form>
      </section>

      <section aria-label="Filtros de gastos externos" className={estilos.filtros}>
        <div className={estilos.fechas}>
          <label>
            Desde
            <input
              onChange={(evento) =>
                setRango((actual) => ({ ...actual, desde: evento.target.value }))
              }
              type="date"
              value={rango.desde}
            />
          </label>
          <label>
            Hasta
            <input
              onChange={(evento) =>
                setRango((actual) => ({ ...actual, hasta: evento.target.value }))
              }
              type="date"
              value={rango.hasta}
            />
          </label>
        </div>
      </section>

      {carga.estado === 'cargando' ? (
        <p role="status">Cargando gastos a externos…</p>
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
        carga.gastos.length === 0 ? (
          <p className={estilos.textoSuave}>
            No hay gastos a externos para el período.
          </p>
        ) : (
          <div className={estilos.tablaContenedor}>
            <table className={estilos.tabla}>
              <caption>Gastos a externos del período</caption>
              <thead>
                <tr>
                  <th scope="col">Fecha</th>
                  <th scope="col">Descripción</th>
                  <th scope="col">Monto</th>
                  <th scope="col">Estado</th>
                  <th scope="col">Acción</th>
                </tr>
              </thead>
              <tbody>
                {carga.gastos.map((gasto) => (
                  <tr key={gasto.id}>
                    <td>{gasto.fecha}</td>
                    <td>{gasto.descripcion}</td>
                    <td>{formatearDinero(gasto.monto_centavos)}</td>
                    <td>
                      {gasto.anulado_en ? (
                        <span>Anulado: {gasto.motivo_anulacion}</span>
                      ) : (
                        'Vigente'
                      )}
                    </td>
                    <td>
                      {gasto.anulado_en ? null : (
                        <Boton
                          onClick={() => {
                            setAAnular(gasto);
                            setMotivo('');
                            setErrorAnular('');
                          }}
                          variante="secundario"
                        >
                          Anular
                        </Boton>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      ) : null}

      <DialogoConfirmacion
        abierto={aAnular !== null}
        descripcion="El gasto no se borra: queda anulado con su motivo."
        onCerrar={() => setAAnular(null)}
        pie={
          <>
            <Boton onClick={() => setAAnular(null)} variante="secundario">
              Cancelar
            </Boton>
            <Boton
              cargando={anulando}
              onClick={confirmarAnulacion}
              variante="peligro"
            >
              Anular gasto
            </Boton>
          </>
        }
        titulo="Anular gasto a externo"
      >
        <Campo
          error={errorAnular}
          etiqueta="Motivo"
          id="gasto-motivo-anulacion"
          obligatorio
        >
          <input
            id="gasto-motivo-anulacion"
            onChange={(evento) => setMotivo(evento.target.value)}
            value={motivo}
          />
        </Campo>
      </DialogoConfirmacion>
    </div>
  );
}
