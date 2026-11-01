import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';

import { BannerDeuda } from '../../../core/components/BannerDeuda';
import { ApiError } from '../../../core/api/client';
import { Alerta } from '../../../core/components/ui/Alerta';
import { Boton } from '../../../core/components/ui/Boton';
import { Campo } from '../../../core/components/ui/Campo';
import { formatearDinero, parsearDinero } from '../../../core/formatos/dinero';
import {
  listarMediosPago,
  obtenerResumenDeuda,
} from '../../cobros/api';
import type { MedioPago, ResumenDeuda } from '../../cobros/tipos';
import { generarIdempotencyKey, crearReserva, leerErrorReserva, mensajeDeError, registrarSena } from '../api';
import { MensajeSinCupo } from '../components/MensajeSinCupo';
import { SelectorMascotas } from '../components/SelectorMascotas';
import { SelectorTramo, type Tramo } from '../components/SelectorTramo';
import { desdeFechaLocal, fechaLocal } from '../fechas';
import type { ErrorReserva, Reserva, ReservaCrear } from '../tipos';
import { buscarPersonas, obtenerPersona } from '../../padron/api';
import type { PersonaDetalle, PersonaResumen } from '../../padron/tipos';
import estilos from '../guarderia.module.css';

type EstadoBusqueda = 'inicial' | 'cargando' | 'listo' | 'error';

type ResultadoBusqueda = {
  texto: string;
  estado: EstadoBusqueda;
  personas: PersonaResumen[];
  error: string;
};

type CargaMascotas = {
  personaId: number;
  datos: PersonaDetalle | null;
  error: string;
};

type CargaDeuda = {
  personaId: number;
  resumen: ResumenDeuda | null;
  error: string;
};

type DatosSena = {
  monto_centavos: number;
  medio: string;
};

type ReservaPendiente = {
  reserva: Reserva;
  solicitud: ReservaCrear;
};

function leerMonto(valor: string): number | null {
  try {
    return parsearDinero(valor);
  } catch {
    return null;
  }
}

function crearTramoInicial(fechaSeleccionada?: string | null): {
  tramo: Tramo;
  error: string | null;
} {
  let fecha = fechaLocal(new Date());
  let error: string | null = null;

  if (fechaSeleccionada) {
    try {
      fecha = fechaLocal(desdeFechaLocal(fechaSeleccionada));
    } catch {
      error = 'La fecha recibida desde el calendario no es válida; revisá el tramo.';
    }
  }

  return {
    tramo: {
      desdeFecha: fecha,
      desdeFranja: 'DIA',
      hastaFecha: fecha,
      hastaFranja: 'DIA',
    },
    error,
  };
}

export function NuevaReserva() {
  const navegar = useNavigate();
  const [parametros] = useSearchParams();
  const [tramoInicial] = useState(() => crearTramoInicial(parametros.get('fecha')));
  const idempotencyKey = useState(generarIdempotencyKey)[0];
  const enviandoRef = useRef(false);
  const seleccionTutorRef = useRef<number | null>(null);

  const [textoBusqueda, setTextoBusqueda] = useState('');
  const [busqueda, setBusqueda] = useState<ResultadoBusqueda | null>(null);
  const [tutor, setTutor] = useState<PersonaResumen | null>(null);
  const [mascotas, setMascotas] = useState<CargaMascotas | null>(null);
  const [reintentoMascotas, setReintentoMascotas] = useState(0);
  const [deuda, setDeuda] = useState<CargaDeuda | null>(null);
  const [reintentoDeuda, setReintentoDeuda] = useState(0);
  const [medios, setMedios] = useState<{
    estado: 'cargando' | 'listo' | 'error';
    datos: MedioPago[];
    error: string;
  }>({ estado: 'cargando', datos: [], error: '' });
  const [reintentoMedios, setReintentoMedios] = useState(0);
  const [mascotasSeleccionadas, setMascotasSeleccionadas] = useState<Set<number>>(
    () => new Set(),
  );
  const [cuidadosExtras, setCuidadosExtras] = useState<Record<number, boolean>>({});
  const [tiposCuidado, setTiposCuidado] = useState<Record<number, string>>({});
  const [tramo, setTramo] = useState<Tramo>(tramoInicial.tramo);
  const [total, setTotal] = useState('');
  const [montoSena, setMontoSena] = useState('');
  const [medioSena, setMedioSena] = useState('');
  const [reservaPendiente, setReservaPendiente] = useState<ReservaPendiente | null>(null);
  const [datosSenaReintento, setDatosSenaReintento] = useState<DatosSena | null>(null);
  const [bloquearSolicitud, setBloquearSolicitud] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [errorEnvio, setErrorEnvio] = useState<{
    mensaje: string;
    conflicto: ErrorReserva | null;
  } | null>(null);

  useEffect(() => {
    let activo = true;

    listarMediosPago()
      .then((respuesta) => {
        if (activo) {
          setMedios({
            estado: 'listo',
            datos: respuesta.filter((medio) => medio.activo),
            error: '',
          });
        }
      })
      .catch((fallo: unknown) => {
        if (activo) {
          setMedios({
            estado: 'error',
            datos: [],
            error: mensajeDeError(fallo),
          });
        }
      });

    return () => {
      activo = false;
    };
  }, [reintentoMedios]);

  useEffect(() => {
    if (!tutor) {
      return;
    }

    const personaId = tutor.id;
    const control = new AbortController();
    let activo = true;

    obtenerPersona(personaId, { signal: control.signal })
      .then((datos) => {
        if (activo && seleccionTutorRef.current === personaId) {
          setMascotas({ personaId, datos, error: '' });
        }
      })
      .catch((fallo: unknown) => {
        if (activo && !control.signal.aborted && seleccionTutorRef.current === personaId) {
          setMascotas({ personaId, datos: null, error: mensajeDeError(fallo) });
        }
      });

    return () => {
      activo = false;
      control.abort();
    };
  }, [tutor, reintentoMascotas]);

  useEffect(() => {
    if (!tutor) {
      return;
    }

    const personaId = tutor.id;
    const control = new AbortController();
    let activo = true;

    obtenerResumenDeuda(personaId, { signal: control.signal })
      .then((resumen) => {
        if (activo && seleccionTutorRef.current === personaId) {
          setDeuda({ personaId, resumen, error: '' });
        }
      })
      .catch((fallo: unknown) => {
        if (activo && !control.signal.aborted && seleccionTutorRef.current === personaId) {
          setDeuda({ personaId, resumen: null, error: mensajeDeError(fallo) });
        }
      });

    return () => {
      activo = false;
      control.abort();
    };
  }, [tutor, reintentoDeuda]);

  const datosMascotas = mascotas?.personaId === tutor?.id ? mascotas : null;
  const cargaDeuda = deuda?.personaId === tutor?.id ? deuda : null;
  const mascotasActivas = useMemo(
    () => datosMascotas?.datos?.mascotas.filter((mascota) => mascota.activo) ?? [],
    [datosMascotas],
  );
  const mapaNombresMascotas = useMemo(
    () => new Map(mascotasActivas.map((mascota) => [mascota.id, mascota.nombre])),
    [mascotasActivas],
  );
  const totalCentavos = leerMonto(total);
  const senaCentavos = leerMonto(montoSena);
  const seleccionActual = [...mascotasSeleccionadas].filter((id) =>
    mascotasActivas.some((mascota) => mascota.id === id),
  );
  const errorCupo = errorEnvio?.conflicto ?? null;
  const bloqueadoTramoMascotasTutor =
    enviando || reservaPendiente !== null || bloquearSolicitud;
  const listaMedios = medios.estado === 'listo' ? medios.datos : [];
  const permiteEnviar =
    tutor !== null &&
    datosMascotas?.datos !== null &&
    datosMascotas?.datos !== undefined &&
    seleccionActual.length > 0 &&
    Boolean(tramo.desdeFecha && tramo.hastaFecha) &&
    totalCentavos !== null &&
    senaCentavos !== null &&
    medioSena.length > 0 &&
    medios.estado === 'listo' &&
    !enviando;

  async function buscarTutor(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    await ejecutarBusqueda(textoBusqueda);
  }

  async function ejecutarBusqueda(consulta: string) {
    const texto = consulta.trim();

    if (!texto) {
      setBusqueda({
        texto,
        estado: 'error',
        personas: [],
        error: 'Ingresá un nombre, apellido o DNI para buscar.',
      });
      return;
    }

    setBusqueda({ texto, estado: 'cargando', personas: [], error: '' });

    try {
      const personas = await buscarPersonas(texto);
      setBusqueda({
        texto,
        estado: 'listo',
        personas,
        error: '',
      });
    } catch (fallo: unknown) {
      setBusqueda({
        texto,
        estado: 'error',
        personas: [],
        error: mensajeDeError(fallo),
      });
    }
  }

  function seleccionarTutor(persona: PersonaResumen) {
    seleccionTutorRef.current = persona.id;
    setTutor(persona);
    setMascotasSeleccionadas(new Set());
    setCuidadosExtras({});
    setTiposCuidado({});
    setMascotas(null);
    setDeuda(null);
    setBusqueda(null);
  }

  function limpiarTutor() {
    seleccionTutorRef.current = null;
    setTutor(null);
    setMascotas(null);
    setDeuda(null);
    setMascotasSeleccionadas(new Set());
    setCuidadosExtras({});
    setTiposCuidado({});
    setErrorEnvio(null);
    setReservaPendiente(null);
    setDatosSenaReintento(null);
    setBloquearSolicitud(false);
  }

  function alternarMascota(pacienteId: number) {
    setMascotasSeleccionadas((actuales) => {
      const nuevas = new Set(actuales);

      if (nuevas.has(pacienteId)) {
        nuevas.delete(pacienteId);
      } else {
        nuevas.add(pacienteId);
      }

      return nuevas;
    });
  }

  function cambiarCuidadosExtras(pacienteId: number, activo: boolean) {
    setCuidadosExtras((actuales) => ({
      ...actuales,
      [pacienteId]: activo,
    }));
    if (!activo) {
      setTiposCuidado((actuales) => ({
        ...actuales,
        [pacienteId]: '',
      }));
    }
  }

  async function enviarReserva(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();

    if (enviandoRef.current || !permiteEnviar || !tutor || totalCentavos === null) {
      return;
    }

    const datosSena: DatosSena =
      datosSenaReintento ?? {
        monto_centavos: senaCentavos!,
        medio: medioSena,
      };
    const solicitud: ReservaCrear =
      reservaPendiente?.solicitud ?? {
        tutor_persona_id: tutor.id,
        paciente_ids: seleccionActual,
        desde_fecha: tramo.desdeFecha,
        desde_franja: tramo.desdeFranja,
        hasta_fecha: tramo.hastaFecha,
        hasta_franja: tramo.hastaFranja,
        cuidados_extras: seleccionActual.map((pacienteId) => ({
          paciente_id: pacienteId,
          cuidados_extras: cuidadosExtras[pacienteId] ?? false,
          tipo_cuidado: cuidadosExtras[pacienteId]
            ? tiposCuidado[pacienteId]?.trim() || null
            : null,
        })),
        total_centavos: totalCentavos,
      };

    enviandoRef.current = true;
    setEnviando(true);
    setErrorEnvio(null);
    let reservaCreada = reservaPendiente !== null;

    try {
      const reserva =
        reservaPendiente?.reserva ??
        (await crearReserva(solicitud, { idempotencyKey }));

      if (!reservaPendiente) {
        setReservaPendiente({ reserva, solicitud });
        reservaCreada = true;
      }

      const confirmada = await registrarSena(
        reserva.id,
        datosSena,
        { idempotencyKey },
      );

      navegar(`/guarderia/reservas/${confirmada.id}`);
    } catch (fallo: unknown) {
      if (fallo instanceof ApiError && fallo.tipo === 'red') {
        if (reservaCreada) {
          setDatosSenaReintento(datosSena);
        } else {
          setBloquearSolicitud(true);
        }
      } else {
        setDatosSenaReintento(null);
      }

      const conflicto = leerErrorReserva(fallo);
      setErrorEnvio({
        mensaje: mensajeDeError(fallo),
        conflicto,
      });
    } finally {
      enviandoRef.current = false;
      setEnviando(false);
    }
  }

  const busquedaActual = busqueda?.texto === textoBusqueda.trim() ? busqueda : null;

  return (
    <section aria-labelledby="titulo-nueva-reserva" className={estilos.pagina}>
      <header className={estilos.cabecera}>
        <div>
          <h1 className={estilos.titulo} id="titulo-nueva-reserva">
            Nueva reserva
          </h1>
          <p className={estilos.subtitulo}>La seña es obligatoria para confirmar el lugar.</p>
        </div>
        <Link className={estilos.enlace} to="/guarderia/calendario">
          Calendario
        </Link>
      </header>

      {tramoInicial.error ? (
        <Alerta role="alert" tono="error">
          {tramoInicial.error}
        </Alerta>
      ) : null}

      {medios.estado === 'cargando' ? (
        <p className={estilos.cargando} role="status">
          Cargando medios de pago…
        </p>
      ) : null}
      {medios.estado === 'error' ? (
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
          No pudimos cargar los medios de pago: {medios.error}
        </Alerta>
      ) : null}
      {medios.estado === 'listo' && listaMedios.length === 0 ? (
        <p className={estilos.vacio}>No hay medios de pago activos.</p>
      ) : null}

      {tutor ? (
        <section aria-label="Tutor elegido" className={estilos.tutorElegido}>
          <div>
            <strong>
              {tutor.apellido}, {tutor.nombre}
            </strong>
            <p>{tutor.dni ? `DNI ${tutor.dni}` : 'Sin DNI registrado'}</p>
          </div>
          {!reservaPendiente && !bloquearSolicitud ? (
            <Boton onClick={limpiarTutor} variante="secundario">
              Cambiar tutor
            </Boton>
          ) : null}
        </section>
      ) : (
        <form className={estilos.formulario} onSubmit={buscarTutor}>
          <Campo
            ayuda="Buscá por nombre, apellido o DNI."
            etiqueta="Tutor"
            id="buscar-tutor"
          >
            <input
              autoComplete="off"
              id="buscar-tutor"
              onChange={(evento) => setTextoBusqueda(evento.currentTarget.value)}
              type="search"
              value={textoBusqueda}
            />
          </Campo>
          <Boton type="submit" variante="secundario">
            Buscar tutor
          </Boton>
          {busquedaActual?.estado === 'cargando' ? (
            <p className={estilos.cargando} role="status">
              Buscando tutores…
            </p>
          ) : null}
          {busquedaActual?.estado === 'error' ? (
            <Alerta role="alert" tono="error">
              {busquedaActual.error}
              {textoBusqueda.trim() ? (
                <Boton
                  onClick={() => void ejecutarBusqueda(textoBusqueda)}
                  variante="secundario"
                >
                  Reintentar búsqueda
                </Boton>
              ) : null}
            </Alerta>
          ) : null}
          {busquedaActual?.estado === 'listo' &&
          busquedaActual.personas.length === 0 ? (
            <p className={estilos.vacio}>No se encontraron tutores.</p>
          ) : null}
          {busquedaActual?.estado === 'listo' &&
          busquedaActual.personas.length > 0 ? (
            <ul aria-label="Resultados de tutores" className={estilos.resultados}>
              {busquedaActual.personas.map((persona) => (
                <li key={persona.id}>
                  <button
                    className={estilos.resultadoTutor}
                    onClick={() => seleccionarTutor(persona)}
                    type="button"
                  >
                    <strong>
                      {persona.apellido}, {persona.nombre}
                    </strong>
                    <span>{persona.dni ? `DNI ${persona.dni}` : 'Sin DNI'}</span>
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
        </form>
      )}

      {tutor && cargaDeuda?.resumen ? (
        <BannerDeuda
          debe={cargaDeuda.resumen.debe}
          deudaMasAntigua={cargaDeuda.resumen.deuda_mas_antigua}
          personaId={tutor.id}
          saldoTotalCentavos={cargaDeuda.resumen.saldo_total_centavos}
        />
      ) : null}
      {tutor && cargaDeuda?.error ? (
        <Alerta
          acciones={
            <Boton
              onClick={() => setReintentoDeuda((valor) => valor + 1)}
              variante="secundario"
            >
              Reintentar
            </Boton>
          }
          role="alert"
          tono="error"
        >
          No pudimos consultar la deuda: {cargaDeuda.error}
        </Alerta>
      ) : null}

      {tutor && !datosMascotas ? (
        <p className={estilos.cargando} role="status">
          Cargando mascotas…
        </p>
      ) : null}
      {tutor && datosMascotas?.error ? (
        <Alerta
          acciones={
            <Boton
              onClick={() => setReintentoMascotas((valor) => valor + 1)}
              variante="secundario"
            >
              Reintentar
            </Boton>
          }
          role="alert"
          tono="error"
        >
          {datosMascotas.error}
        </Alerta>
      ) : null}

      {tutor && datosMascotas?.datos ? (
        <form className={estilos.formulario} onSubmit={enviarReserva}>
          <SelectorMascotas
            bloqueado={bloqueadoTramoMascotasTutor}
            cuidadosExtras={cuidadosExtras}
            mascotas={mascotasActivas}
            onCuidadoExtraChange={cambiarCuidadosExtras}
            onTipoCuidadoChange={(pacienteId, tipo) =>
              setTiposCuidado((actuales) => ({
                ...actuales,
                [pacienteId]: tipo,
              }))
            }
            onToggle={alternarMascota}
            seleccionadas={mascotasSeleccionadas}
            tiposCuidado={tiposCuidado}
          />

          <SelectorTramo
            bloqueado={bloqueadoTramoMascotasTutor}
            onChange={setTramo}
            tramo={tramo}
          />

          <fieldset
            className={estilos.grupoFormulario}
            disabled={bloqueadoTramoMascotasTutor}
          >
            <legend>Total provisorio</legend>
            <div className={estilos.grillaFormulario}>
              <Campo
                ayuda="Importe provisorio; se cotizará automáticamente cuando esté disponible."
                etiqueta="Total provisorio"
                id="total-provisorio"
              >
                <input
                  id="total-provisorio"
                  inputMode="decimal"
                  onChange={(evento) => setTotal(evento.currentTarget.value)}
                  placeholder="0,00"
                  type="text"
                  value={total}
                />
              </Campo>
            </div>
            {totalCentavos !== null ? (
              <p className={estilos.importeResumen}>
                Total: {formatearDinero(totalCentavos)}
              </p>
            ) : null}
            {total.trim() && totalCentavos === null ? (
              <p className={estilos.errorTexto}>Ingresá un total mayor a cero.</p>
            ) : null}
          </fieldset>

          <fieldset
            className={estilos.grupoFormulario}
            disabled={enviando || datosSenaReintento !== null}
          >
            <legend>Seña obligatoria</legend>
            <div className={estilos.grillaFormulario}>
              <Campo
                ayuda="Monto libre, mayor a cero."
                etiqueta="Seña obligatoria"
                id="monto-sena"
              >
                <input
                  id="monto-sena"
                  inputMode="decimal"
                  onChange={(evento) => setMontoSena(evento.currentTarget.value)}
                  placeholder="0,00"
                  required
                  type="text"
                  value={montoSena}
                />
              </Campo>
              <Campo etiqueta="Medio de pago de la seña" id="medio-sena">
                <select
                  id="medio-sena"
                  onChange={(evento) => setMedioSena(evento.currentTarget.value)}
                  required
                  value={medioSena}
                >
                  <option value="">Elegir medio</option>
                  {listaMedios.map((medio) => (
                    <option key={medio.codigo} value={medio.codigo}>
                      {medio.nombre}
                    </option>
                  ))}
                </select>
              </Campo>
            </div>
            {montoSena.trim() && senaCentavos === null ? (
              <p className={estilos.errorTexto}>La seña debe ser un monto mayor a cero.</p>
            ) : null}
          </fieldset>

          {errorCupo ? (
            <MensajeSinCupo error={errorCupo} nombresMascotas={mapaNombresMascotas} />
          ) : errorEnvio ? (
            <Alerta role="alert" tono="error">
              {errorEnvio.mensaje}
            </Alerta>
          ) : null}

          <Boton
            bloque
            cargando={enviando}
            disabled={!permiteEnviar}
            type="submit"
          >
            {errorEnvio ? 'Reintentar reserva' : 'Reservar'}
          </Boton>
        </form>
      ) : null}
    </section>
  );
}
