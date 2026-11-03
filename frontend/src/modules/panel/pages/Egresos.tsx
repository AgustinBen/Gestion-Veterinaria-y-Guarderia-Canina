import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';

import { Alerta } from '../../../core/components/ui/Alerta';
import { Boton } from '../../../core/components/ui/Boton';
import { Campo } from '../../../core/components/ui/Campo';
import { DialogoConfirmacion } from '../../../core/components/ui/DialogoConfirmacion';
import { formatearDinero, parsearDinero } from '../../../core/formatos/dinero';
import {
  anularEgreso,
  crearEgreso,
  generarIdempotencyKey,
  listarCategoriasEgreso,
  listarEgresos,
  mensajeDeError,
} from '../api';
import { calcularRango, fechaIsoLocal } from '../components/filtrosPanel';
import type { CategoriaEgreso, Egreso } from '../tipos';
import estilos from '../panel.module.css';

type Estado =
  | { estado: 'cargando' }
  | { estado: 'error'; error: string }
  | { estado: 'listo'; egresos: Egreso[]; categorias: CategoriaEgreso[] };

function rangoInicial(): { desde: string; hasta: string } {
  return calcularRango('mes');
}

/** Alta, listado y anulación de egresos operativos (T-38 / T-50). */
export function Egresos() {
  const [carga, setCarga] = useState<Estado>({ estado: 'cargando' });
  const [reintento, setReintento] = useState(0);
  const [rango, setRango] = useState(rangoInicial);
  const [categoriaFiltro, setCategoriaFiltro] = useState('');
  const [fecha, setFecha] = useState(() => fechaIsoLocal(new Date()));
  const [monto, setMonto] = useState('');
  const [categoriaId, setCategoriaId] = useState('');
  const [descripcion, setDescripcion] = useState('');
  const [errorAlta, setErrorAlta] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [aAnular, setAAnular] = useState<Egreso | null>(null);
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

    Promise.all([
      listarCategoriasEgreso({ signal: control.signal }),
      listarEgresos(
        {
          desde: rango.desde,
          hasta: rango.hasta,
          categoriaId: categoriaFiltro ? Number(categoriaFiltro) : null,
        },
        { signal: control.signal },
      ),
    ])
      .then(([categorias, egresos]) => {
        if (control.signal.aborted) {
          return;
        }

        setCarga({ estado: 'listo', categorias, egresos });
        setCategoriaId((actual) => {
          if (actual) {
            return actual;
          }
          return String(categorias.find((item) => item.activa)?.id ?? '');
        });
      })
      .catch((fallo) => {
        if (!control.signal.aborted) {
          setCarga({ estado: 'error', error: mensajeDeError(fallo) });
        }
      });

    return () => control.abort();
  }, [rango.desde, rango.hasta, categoriaFiltro, reintento]);

  const categorias = carga.estado === 'listo' ? carga.categorias : [];
  const activas = categorias.filter((categoria) => categoria.activa);

  async function registrar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();

    if (enviandoRef.current) {
      return;
    }

    if (categorias.length === 0) {
      setErrorAlta('Primero creá una categoría de egreso.');
      return;
    }

    let montoCentavos: number;

    try {
      montoCentavos = parsearDinero(monto);
    } catch (fallo) {
      setErrorAlta(fallo instanceof Error ? fallo.message : 'Monto inválido.');
      return;
    }

    if (!categoriaId) {
      setErrorAlta('Elegí una categoría.');
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
      await crearEgreso(
        {
          fecha,
          monto_centavos: montoCentavos,
          categoria_id: Number(categoriaId),
          descripcion: descripcion.trim(),
        },
        { idempotencyKey },
      );
      setMonto('');
      setDescripcion('');
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
      await anularEgreso(aAnular.id, motivo.trim());
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
          <h1 className={estilos.titulo}>Egresos operativos</h1>
          <p className={estilos.subtitulo}>
            Registrá y anulá los gastos operativos del negocio.
          </p>
          <Link className={`${estilos.enlace} ${estilos.volver}`} to="/panel">
            Volver al panel
          </Link>
        </div>
        <nav aria-label="Secciones del panel" className={estilos.navegacion}>
          <Link to="/panel/gastos-externos">Gastos a externos</Link>
          <Link to="/panel/categorias">Categorías</Link>
        </nav>
      </div>

      {carga.estado === 'listo' && categorias.length === 0 ? (
        <Alerta
          acciones={
            <Link className={estilos.enlace} to="/panel/categorias">
              Crear la primera categoría
            </Link>
          }
          role="alert"
          tono="aviso"
        >
          Todavía no hay categorías de egreso. Creá una antes de registrar un
          egreso.
        </Alerta>
      ) : null}

      <section aria-label="Nuevo egreso" className={estilos.tarjeta}>
        <h2>Registrar egreso</h2>
        <form className={estilos.formulario} onSubmit={registrar}>
          <Campo etiqueta="Fecha" id="egreso-fecha">
            <input
              id="egreso-fecha"
              onChange={(evento) => setFecha(evento.target.value)}
              type="date"
              value={fecha}
            />
          </Campo>

          <Campo etiqueta="Monto" id="egreso-monto">
            <input
              id="egreso-monto"
              inputMode="decimal"
              onChange={(evento) => setMonto(evento.target.value)}
              placeholder="10.000 o 10.000,50"
              value={monto}
            />
          </Campo>

          <Campo etiqueta="Categoría" id="egreso-categoria">
            <select
              id="egreso-categoria"
              onChange={(evento) => setCategoriaId(evento.target.value)}
              value={categoriaId}
            >
              <option value="">Seleccionar categoría</option>
              {activas.map((categoria) => (
                <option key={categoria.id} value={categoria.id}>
                  {categoria.nombre}
                </option>
              ))}
            </select>
          </Campo>

          <Campo etiqueta="Descripción" id="egreso-descripcion">
            <input
              id="egreso-descripcion"
              onChange={(evento) => setDescripcion(evento.target.value)}
              value={descripcion}
            />
          </Campo>

          {errorAlta ? (
            <Alerta role="alert" tono="error">
              {errorAlta}
            </Alerta>
          ) : null}

          <Boton
            cargando={enviando}
            disabled={categorias.length === 0}
            type="submit"
          >
            Registrar egreso
          </Boton>
        </form>
      </section>

      <section aria-label="Filtros de egresos" className={estilos.filtros}>
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
          <label>
            Categoría
            <select
              onChange={(evento) => setCategoriaFiltro(evento.target.value)}
              value={categoriaFiltro}
            >
              <option value="">Todas</option>
              {categorias.map((categoria) => (
                <option key={categoria.id} value={categoria.id}>
                  {categoria.nombre}
                </option>
              ))}
            </select>
          </label>
        </div>
      </section>

      {carga.estado === 'cargando' ? (
        <p role="status">Cargando egresos…</p>
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
        carga.egresos.length === 0 ? (
          <p className={estilos.textoSuave}>
            No hay egresos registrados para el período.
          </p>
        ) : (
          <div className={estilos.tablaContenedor}>
            <table className={estilos.tabla}>
              <caption>Egresos del período</caption>
              <thead>
                <tr>
                  <th scope="col">Fecha</th>
                  <th scope="col">Categoría</th>
                  <th scope="col">Descripción</th>
                  <th scope="col">Monto</th>
                  <th scope="col">Estado</th>
                  <th scope="col">Acción</th>
                </tr>
              </thead>
              <tbody>
                {carga.egresos.map((egreso) => (
                  <tr key={egreso.id}>
                    <td>{egreso.fecha}</td>
                    <td>{egreso.categoria_nombre}</td>
                    <td>{egreso.descripcion}</td>
                    <td>{formatearDinero(egreso.monto_centavos)}</td>
                    <td>
                      {egreso.anulado_en ? (
                        <span>Anulado: {egreso.motivo_anulacion}</span>
                      ) : (
                        'Vigente'
                      )}
                    </td>
                    <td>
                      {egreso.anulado_en ? null : (
                        <Boton
                          onClick={() => {
                            setAAnular(egreso);
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
        descripcion="El egreso no se borra: queda anulado con su motivo."
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
              Anular egreso
            </Boton>
          </>
        }
        titulo="Anular egreso"
      >
        <Campo
          error={errorAnular}
          etiqueta="Motivo"
          id="egreso-motivo-anulacion"
        >
          <input
            id="egreso-motivo-anulacion"
            onChange={(evento) => setMotivo(evento.target.value)}
            value={motivo}
          />
        </Campo>
      </DialogoConfirmacion>
    </div>
  );
}
