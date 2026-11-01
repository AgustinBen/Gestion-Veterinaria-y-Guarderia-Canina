import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, useParams } from 'react-router-dom';

import { ApiError } from '../../../core/api/client';
import { Alerta } from '../../../core/components/ui/Alerta';
import { Boton } from '../../../core/components/ui/Boton';
import { Campo } from '../../../core/components/ui/Campo';
import { formatearDinero, parsearDinero } from '../../../core/formatos/dinero';
import { listarMediosPago } from '../../cobros/api';
import type { MedioPago } from '../../cobros/tipos';
import { obtenerPaciente } from '../../padron/api';
import type { PacienteDetalle } from '../../padron/tipos';
import { generarIdempotencyKey, mensajeDeError, obtenerReserva, registrarSena } from '../api';
import { formatoFechaReserva } from '../fechas';
import { usePuedeEscribirReservas } from '../permisos';
import type { EstadoReserva, Reserva, ReservaSenaCrear } from '../tipos';
import estilos from '../guarderia.module.css';

type CargaDetalle = {
  id: number;
  reserva: Reserva;
  mascotas: PacienteDetalle[];
};

type DatosCarga = {
  id: number;
  datos: CargaDetalle | null;
  error: string;
};

type DatosSenaReintento = ReservaSenaCrear;

const ETIQUETAS_ESTADO: Record<EstadoReserva, string> = {
  PENDIENTE_SENA: 'Pendiente de seña',
  CONFIRMADA: 'Confirmada',
  EN_CURSO: 'En curso',
  FINALIZADA: 'Finalizada',
  CANCELADA: 'Cancelada',
  AUSENTE: 'Ausente',
};

const ETIQUETAS_FRANJA = {
  DIA: 'día',
  NOCHE: 'noche',
} as const;

function numeroPositivo(valor: string | undefined): number | null {
  if (!valor) {
    return null;
  }

  const numero = Number(valor);

  return Number.isSafeInteger(numero) && numero > 0 ? numero : null;
}

function leerMonto(valor: string): number | null {
  try {
    return parsearDinero(valor);
  } catch {
    return null;
  }
}

export function DetalleReserva() {
  const { reservaId } = useParams();
  const id = numeroPositivo(reservaId);
  const puedeEscribir = usePuedeEscribirReservas();
  const idempotencyKey = useState(generarIdempotencyKey)[0];
  const enviandoRef = useRef(false);
  const [intento, setIntento] = useState(0);
  const [carga, setCarga] = useState<DatosCarga | null>(null);
  const [formularioAbierto, setFormularioAbierto] = useState(false);
  const [medios, setMedios] = useState<{
    id: number | null;
    estado: 'cargando' | 'listo' | 'error';
    datos: MedioPago[];
    error: string;
  }>({ id: null, estado: 'cargando', datos: [], error: '' });
  const [reintentoMedios, setReintentoMedios] = useState(0);
  const [montoSena, setMontoSena] = useState('');
  const [medioSena, setMedioSena] = useState('');
  const [datosReintento, setDatosReintento] = useState<DatosSenaReintento | null>(
    null,
  );
  const [enviando, setEnviando] = useState(false);
  const [errorSena, setErrorSena] = useState('');

  useEffect(() => {
    const reservaIdActual = id;

    if (reservaIdActual === null) {
      return;
    }
    const reservaIdValido: number = reservaIdActual;

    const control = new AbortController();
    let activo = true;

    async function cargar() {
      try {
        const reserva = await obtenerReserva(reservaIdValido, {
          signal: control.signal,
        });
        const mascotas = await Promise.all(
          reserva.pacientes.map(({ paciente_id }) =>
            obtenerPaciente(paciente_id, { signal: control.signal }),
          ),
        );

        if (activo && !control.signal.aborted) {
          setCarga({
            id: reservaIdValido,
            datos: { id: reservaIdValido, reserva, mascotas },
            error: '',
          });
        }
      } catch (fallo: unknown) {
        if (activo && !control.signal.aborted) {
          setCarga({
            id: reservaIdValido,
            datos: null,
            error: mensajeDeError(fallo),
          });
        }
      }
    }

    void cargar();

    return () => {
      activo = false;
      control.abort();
    };
  }, [id, intento]);

  const datos = carga?.id === id ? carga.datos : null;
  const errorCarga = carga?.id === id ? carga.error : '';

  useEffect(() => {
    const reservaIdActual = id;

    if (
      reservaIdActual === null ||
      !puedeEscribir ||
      !datos ||
      datos.reserva.estado !== 'PENDIENTE_SENA'
    ) {
      return;
    }
    const reservaIdValido: number = reservaIdActual;

    let activo = true;

    listarMediosPago()
      .then((respuesta) => {
        if (activo) {
          setMedios({
            id: reservaIdValido,
            estado: 'listo',
            datos: respuesta.filter((medio) => medio.activo),
            error: '',
          });
        }
      })
      .catch((fallo: unknown) => {
        if (activo) {
          setMedios({
            id: reservaIdValido,
            estado: 'error',
            datos: [],
            error: mensajeDeError(fallo),
          });
        }
      });

    return () => {
      activo = false;
    };
  }, [datos, id, puedeEscribir, reintentoMedios]);

  if (id === null) {
    return (
      <section className={estilos.pagina}>
        <Alerta role="alert" tono="error">
          El número de reserva no es válido.
        </Alerta>
        <Link className={estilos.enlace} to="/guarderia/calendario">
          Volver al calendario
        </Link>
      </section>
    );
  }

  if (!datos && !errorCarga) {
    return (
      <section className={estilos.pagina}>
        <h1 className={estilos.titulo}>Detalle de reserva</h1>
        <p className={estilos.cargando} role="status">
          Cargando reserva…
        </p>
      </section>
    );
  }

  if (errorCarga || !datos) {
    return (
      <section className={estilos.pagina}>
        <h1 className={estilos.titulo}>Detalle de reserva</h1>
        <Alerta
          acciones={
            <Boton onClick={() => setIntento((valor) => valor + 1)} variante="secundario">
              Reintentar
            </Boton>
          }
          role="alert"
          tono="error"
        >
          {errorCarga || 'No pudimos cargar la reserva.'}
        </Alerta>
        <Link className={estilos.enlace} to="/guarderia/calendario">
          Volver al calendario
        </Link>
      </section>
    );
  }

  const cargaActual: CargaDetalle = datos;
  const { reserva, mascotas } = cargaActual;
  const metodosPago = medios.id === id && medios.estado === 'listo' ? medios.datos : [];
  const centavosSena = leerMonto(montoSena);
  const habilitarEnvio =
    centavosSena !== null &&
    medioSena.length > 0 &&
    medios.estado === 'listo' &&
    !enviando;

  async function enviarSena(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();

    if (enviandoRef.current || !habilitarEnvio || centavosSena === null) {
      return;
    }

    const solicitud: ReservaSenaCrear =
      datosReintento ?? { monto_centavos: centavosSena, medio: medioSena };

    enviandoRef.current = true;
    setEnviando(true);
    setErrorSena('');

    try {
      const actualizada = await registrarSena(reserva.id, solicitud, {
        idempotencyKey,
      });
      setCarga({
        id: cargaActual.id,
        datos: { ...cargaActual, reserva: actualizada },
        error: '',
      });
      setFormularioAbierto(false);
      setDatosReintento(null);
      setMontoSena('');
      setMedioSena('');
    } catch (fallo: unknown) {
      if (fallo instanceof ApiError && fallo.tipo === 'red') {
        setDatosReintento(solicitud);
      } else {
        setDatosReintento(null);
      }
      setErrorSena(mensajeDeError(fallo));
    } finally {
      enviandoRef.current = false;
      setEnviando(false);
    }
  }

  const tramo = `${formatoFechaReserva(reserva.desde_fecha)} (${ETIQUETAS_FRANJA[reserva.desde_franja]}) – ${formatoFechaReserva(reserva.hasta_fecha)} (${ETIQUETAS_FRANJA[reserva.hasta_franja]})`;

  return (
    <section aria-labelledby="titulo-detalle-reserva" className={estilos.pagina}>
      <header className={estilos.cabecera}>
        <div>
          <h1 className={estilos.titulo} id="titulo-detalle-reserva">
            Reserva #{reserva.id}
          </h1>
          <p className={estilos.subtitulo}>Detalle de estadía de guardería.</p>
        </div>
        <Link className={estilos.enlace} to="/guarderia/calendario">
          Volver al calendario
        </Link>
      </header>

      <dl className={estilos.detalleReserva}>
        <div>
          <dt>Estado</dt>
          <dd>{ETIQUETAS_ESTADO[reserva.estado]}</dd>
        </div>
        <div>
          <dt>Tramo</dt>
          <dd>{tramo}</dd>
        </div>
        <div>
          <dt>Total</dt>
          <dd>
            {reserva.total_centavos === null
              ? 'No disponible'
              : formatearDinero(reserva.total_centavos)}
          </dd>
        </div>
        <div>
          <dt>Seña</dt>
          <dd>
            {formatearDinero(reserva.sena_centavos)}
            {reserva.estado === 'PENDIENTE_SENA' ? ' · Pendiente' : ''}
          </dd>
        </div>
      </dl>

      <section aria-labelledby="mascotas-reserva">
        <h2 className={estilos.tituloSeccion} id="mascotas-reserva">
          Mascotas
        </h2>
        {mascotas.length === 0 ? (
          <p className={estilos.vacio}>La reserva no tiene mascotas asociadas.</p>
        ) : (
          <ul className={estilos.listaMascotas}>
            {mascotas.map((mascota) => {
              const datosReserva = reserva.pacientes.find(
                (paciente) => paciente.paciente_id === mascota.id,
              );

              return (
                <li className={estilos.mascota} key={mascota.id}>
                  <strong>
                    {mascota.nombre} · {mascota.especie_nombre}
                  </strong>
                  <span>
                    Cuidados extras: {datosReserva?.cuidados_extras ? 'Sí' : 'No'}
                  </span>
                  {datosReserva?.tipo_cuidado ? (
                    <span>Tipo de cuidado: {datosReserva.tipo_cuidado}</span>
                  ) : null}
                </li>
              );
            })}
          </ul>
        )}
      </section>

      {puedeEscribir && reserva.estado === 'PENDIENTE_SENA' ? (
        <section className={estilos.seccionAcciones}>
          <Boton
            onClick={() => setFormularioAbierto((abierto) => !abierto)}
            variante="secundario"
          >
            Registrar seña
          </Boton>
          {formularioAbierto ? (
            <form className={estilos.formulario} onSubmit={enviarSena}>
              <Campo etiqueta="Monto de la seña" id="detalle-monto-sena">
                <input
                  disabled={enviando || datosReintento !== null}
                  id="detalle-monto-sena"
                  inputMode="decimal"
                  onChange={(evento) => setMontoSena(evento.currentTarget.value)}
                  required
                  type="text"
                  value={montoSena}
                />
              </Campo>
              <Campo etiqueta="Medio de pago" id="detalle-medio-sena">
                <select
                  disabled={enviando || datosReintento !== null}
                  id="detalle-medio-sena"
                  onChange={(evento) => setMedioSena(evento.currentTarget.value)}
                  required
                  value={medioSena}
                >
                  <option value="">Elegir medio</option>
                  {metodosPago.map((medio) => (
                    <option key={medio.codigo} value={medio.codigo}>
                      {medio.nombre}
                    </option>
                  ))}
                </select>
              </Campo>
              {medios.id !== id || medios.estado === 'cargando' ? (
                <p className={estilos.cargando} role="status">
                  Cargando medios de pago…
                </p>
              ) : null}
              {medios.id === id && medios.estado === 'error' ? (
                <Alerta
                  acciones={
                    <Boton
                      onClick={() => setReintentoMedios((valor) => valor + 1)}
                      variante="secundario"
                    >
                      Reintentar
                    </Boton>
                  }
                  role="alert"
                  tono="error"
                >
                  {medios.error}
                </Alerta>
              ) : null}
              {medios.id === id && medios.estado === 'listo' && metodosPago.length === 0 ? (
                <p className={estilos.vacio}>No hay medios de pago activos.</p>
              ) : null}
              {errorSena ? (
                <Alerta role="alert" tono="error">
                  {errorSena}
                </Alerta>
              ) : null}
              {montoSena.trim() && centavosSena === null ? (
                <p className={estilos.errorTexto}>La seña debe ser mayor a cero.</p>
              ) : null}
              <Boton
                cargando={enviando}
                disabled={!habilitarEnvio}
                type="submit"
              >
                {errorSena ? 'Reintentar registro' : 'Confirmar seña'}
              </Boton>
            </form>
          ) : null}
        </section>
      ) : null}
    </section>
  );
}
