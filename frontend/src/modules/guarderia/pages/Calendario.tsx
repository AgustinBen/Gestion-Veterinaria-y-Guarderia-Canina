import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';

import { useAuth } from '../../../core/auth/contexto';
import { puedeAcceder } from '../../../core/auth/permisos';
import { Boton } from '../../../core/components/ui/Boton';
import { Campo } from '../../../core/components/ui/Campo';
import {
  generarIdempotencyKey,
  habilitarPlazaEmergencia,
  listarCalendario,
  listarReservas,
  mensajeDeError,
} from '../api';
import { fechaLocal } from '../fechas';
import type { Disponibilidad, Franja, Reserva } from '../tipos';
import estilos from './Calendario.module.css';

const DIAS_SEMANA = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];

function primerDiaDelMes(fecha: Date): Date {
  return new Date(fecha.getFullYear(), fecha.getMonth(), 1);
}

function diasDelMes(fecha: Date): (number | null)[] {
  const primerDia = primerDiaDelMes(fecha);
  const espaciosPrevios = (primerDia.getDay() + 6) % 7;
  const cantidad = new Date(
    fecha.getFullYear(),
    fecha.getMonth() + 1,
    0,
  ).getDate();
  const celdas = espaciosPrevios + cantidad;
  const cantidadCeldas = Math.ceil(celdas / 7) * 7;

  return Array.from({ length: cantidadCeldas }, (_, indice) => {
    const dia = indice - espaciosPrevios + 1;
    return dia > 0 && dia <= cantidad ? dia : null;
  });
}

function nombreMes(fecha: Date, opciones: Intl.DateTimeFormatOptions): string {
  return new Intl.DateTimeFormat('es-AR', opciones).format(fecha);
}

function nombreMesYAnio(fecha: Date): string {
  const mes = nombreMes(fecha, { month: 'long' });
  return `${mes.charAt(0).toLocaleUpperCase('es-AR')}${mes.slice(1)} ${fecha.getFullYear()}`;
}

function IconoAgenda({ tipo }: { tipo: 'guarderia' | 'clinica' }) {
  return tipo === 'guarderia' ? (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <rect x="3.5" y="5" width="17" height="16" rx="2.5" />
      <path d="M7.5 3v4M16.5 3v4M3.5 9.5h17M8 13h.01M12 13h.01M16 13h.01M8 17h.01M12 17h.01" />
    </svg>
  ) : (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M7 3.5h7l4 4v13H7a2 2 0 0 1-2-2v-13a2 2 0 0 1 2-2Z" />
      <path d="M14 3.5v4h4M8.5 12h7M8.5 16h7" />
    </svg>
  );
}

function EsHoy(fecha: Date, dia: number): boolean {
  const hoy = new Date();
  return (
    fecha.getFullYear() === hoy.getFullYear() &&
    fecha.getMonth() === hoy.getMonth() &&
    dia === hoy.getDate()
  );
}

type CargaAgenda =
  | {
      periodo: string;
      estado: 'cargando';
      disponibilidad: Disponibilidad[];
      reservas: Reserva[];
    }
  | {
      periodo: string;
      estado: 'error';
      disponibilidad: Disponibilidad[];
      reservas: Reserva[];
      error: string;
    }
  | {
      periodo: string;
      estado: 'lista';
      disponibilidad: Disponibilidad[];
      reservas: Reserva[];
    };

function franjasDeReservaEnFecha(reserva: Reserva, fecha: string): Franja[] {
  if (fecha < reserva.desde_fecha || fecha > reserva.hasta_fecha) {
    return [];
  }

  if (reserva.desde_fecha === reserva.hasta_fecha) {
    return reserva.desde_franja === reserva.hasta_franja
      ? [reserva.desde_franja]
      : ['DIA', 'NOCHE'];
  }

  if (fecha === reserva.desde_fecha) {
    return reserva.desde_franja === 'DIA' ? ['DIA', 'NOCHE'] : ['NOCHE'];
  }

  if (fecha === reserva.hasta_fecha) {
    return reserva.hasta_franja === 'NOCHE' ? ['DIA', 'NOCHE'] : ['DIA'];
  }

  return ['DIA', 'NOCHE'];
}

function nombreFranja(franja: Franja): string {
  return franja === 'DIA' ? 'Día' : 'Noche';
}

export function Calendario() {
  const [fechaSeleccionada, setFechaSeleccionada] = useState(() => new Date());
  const [reintento, setReintento] = useState(0);
  const [carga, setCarga] = useState<CargaAgenda>({
    periodo: '',
    estado: 'cargando',
    disponibilidad: [],
    reservas: [],
  });
  const [emergenciaAbierta, setEmergenciaAbierta] = useState(false);
  const [franjaEmergencia, setFranjaEmergencia] = useState<Franja>('DIA');
  const [motivoEmergencia, setMotivoEmergencia] = useState('');
  const [claveEmergencia, setClaveEmergencia] = useState(generarIdempotencyKey);
  const [enviandoEmergencia, setEnviandoEmergencia] = useState(false);
  const [errorEmergencia, setErrorEmergencia] = useState('');
  const enviandoEmergenciaRef = useRef(false);
  const { sesion } = useAuth();
  const soloLectura = sesion
    ? !puedeAcceder(sesion.rol, 'calendario', 'escritura')
    : false;
  const esDuenio = sesion?.rol === 'DUENIO';
  const anioVisible = fechaSeleccionada.getFullYear();
  const indiceMesVisible = fechaSeleccionada.getMonth();
  const periodoVisible = `${anioVisible}-${indiceMesVisible}`;
  const mesVisible = primerDiaDelMes(fechaSeleccionada);
  const dias = diasDelMes(mesVisible);
  const fechaSeleccionadaISO = fechaLocal(fechaSeleccionada);
  const fechaLarga = `${fechaSeleccionada.getDate()} de ${nombreMes(fechaSeleccionada, {
    month: 'long',
  })}`;
  const cargaDelMes: CargaAgenda =
    carga.periodo === periodoVisible
      ? carga
      : {
          periodo: periodoVisible,
          estado: 'cargando',
          disponibilidad: [],
          reservas: [],
        };
  const reservasDelDia =
    cargaDelMes.estado === 'lista'
      ? cargaDelMes.reservas.filter(
          (reserva) =>
            reserva.estado !== 'CANCELADA' &&
            franjasDeReservaEnFecha(reserva, fechaSeleccionadaISO).length > 0,
        )
      : [];
  const disponibilidadEmergencia =
    cargaDelMes.estado === 'lista'
      ? cargaDelMes.disponibilidad.find(
          (item) =>
            item.fecha === fechaSeleccionadaISO &&
            item.franja === franjaEmergencia,
        )
      : undefined;
  const emergenciaAgotada =
    disponibilidadEmergencia !== undefined &&
    disponibilidadEmergencia.habilitadas >=
      disponibilidadEmergencia.plazas_emergencia;
  const todasLasEmergenciasAgotadas =
    cargaDelMes.estado === 'lista' &&
    (['DIA', 'NOCHE'] as const).every((franja) => {
      const disponibilidad = cargaDelMes.disponibilidad.find(
        (item) => item.fecha === fechaSeleccionadaISO && item.franja === franja,
      );
      return (
        disponibilidad !== undefined &&
        disponibilidad.habilitadas >= disponibilidad.plazas_emergencia
      );
    });

  useEffect(() => {
    const controlador = new AbortController();
    const desde = fechaLocal(new Date(anioVisible, indiceMesVisible, 1));
    const hasta = fechaLocal(new Date(anioVisible, indiceMesVisible + 1, 0));

    Promise.all([
      listarCalendario(desde, hasta, { signal: controlador.signal }),
      listarReservas(desde, hasta, { signal: controlador.signal }),
    ])
      .then(([disponibilidad, reservas]) => {
        if (!controlador.signal.aborted) {
          setCarga({
            periodo: periodoVisible,
            estado: 'lista',
            disponibilidad,
            reservas,
          });
        }
      })
      .catch((error: unknown) => {
        if (!controlador.signal.aborted) {
          setCarga({
            periodo: periodoVisible,
            estado: 'error',
            disponibilidad: [],
            reservas: [],
            error: mensajeDeError(error),
          });
        }
      });

    return () => controlador.abort();
  }, [anioVisible, indiceMesVisible, periodoVisible, reintento]);

  function cambiarMes(desplazamiento: number) {
    setEmergenciaAbierta(false);
    setErrorEmergencia('');
    setClaveEmergencia(generarIdempotencyKey());
    setFechaSeleccionada((actual) => {
      const inicioMesSiguiente = new Date(
        actual.getFullYear(),
        actual.getMonth() + desplazamiento,
        1,
      );
      const ultimoDia = new Date(
        inicioMesSiguiente.getFullYear(),
        inicioMesSiguiente.getMonth() + 1,
        0,
      ).getDate();

      return new Date(
        inicioMesSiguiente.getFullYear(),
        inicioMesSiguiente.getMonth(),
        Math.min(actual.getDate(), ultimoDia),
      );
    });
  }

  async function enviarHabilitacionEmergencia(
    evento: FormEvent<HTMLFormElement>,
  ) {
    evento.preventDefault();

    if (enviandoEmergenciaRef.current || !motivoEmergencia.trim()) {
      return;
    }

    enviandoEmergenciaRef.current = true;
    setEnviandoEmergencia(true);
    setErrorEmergencia('');

    try {
      await habilitarPlazaEmergencia(
        {
          fecha: fechaSeleccionadaISO,
          franja: franjaEmergencia,
          motivo: motivoEmergencia.trim(),
        },
        { idempotencyKey: claveEmergencia },
      );
      setEmergenciaAbierta(false);
      setMotivoEmergencia('');
      setClaveEmergencia(generarIdempotencyKey());
      setReintento((actual) => actual + 1);
    } catch (error: unknown) {
      setErrorEmergencia(mensajeDeError(error));
    } finally {
      enviandoEmergenciaRef.current = false;
      setEnviandoEmergencia(false);
    }
  }

  return (
    <section className={estilos.pagina} aria-labelledby="titulo-calendario">
      <header className={estilos.encabezado}>
        <p className={estilos.antetitulo}>Guardería y clínica</p>
        <div className={estilos.filaTitulo}>
          <h1 id="titulo-calendario">Calendario de agenda</h1>
          {soloLectura ? (
            <span className={estilos.insignia}>Solo lectura</span>
          ) : null}
        </div>
        <p className={estilos.descripcion}>
          {nombreMesYAnio(mesVisible)} ·
          {' '}Seleccioná un día para ver la actividad.
        </p>
        {cargaDelMes.estado === 'error' ? (
          <div className={estilos.errorCarga}>
            <p role="alert">No pudimos cargar el calendario: {cargaDelMes.error}</p>
            <button onClick={() => setReintento((actual) => actual + 1)} type="button">
              Reintentar
            </button>
          </div>
        ) : null}
      </header>

      <div className={estilos.disposicion}>
        <section className={estilos.tarjetaCalendario} aria-label="Calendario mensual">
          <div className={estilos.encabezadoMes}>
            <button
              aria-label="Mes anterior"
              onClick={() => cambiarMes(-1)}
              type="button"
            >
              ‹
            </button>
            <h2>{nombreMesYAnio(mesVisible)}</h2>
            <button
              aria-label="Mes siguiente"
              onClick={() => cambiarMes(1)}
              type="button"
            >
              ›
            </button>
          </div>
          <div className={estilos.diasSemana} aria-hidden="true">
            {DIAS_SEMANA.map((dia) => (
              <span key={dia}>{dia}</span>
            ))}
          </div>
          <div className={estilos.grilla} role="group" aria-label="Días del mes">
            {dias.map((dia, indice) =>
              dia === null ? (
                <span
                  aria-hidden="true"
                  className={estilos.diaVacio}
                  key={`vacio-${indice}`}
                />
              ) : (
                <button
                  aria-current={EsHoy(mesVisible, dia) ? 'date' : undefined}
                  aria-label={`${dia} de ${nombreMes(mesVisible, { month: 'long', year: 'numeric' })}`}
                  aria-pressed={fechaSeleccionada.getDate() === dia}
                  className={estilos.dia}
                  key={dia}
                  onClick={() => {
                    setEmergenciaAbierta(false);
                    setErrorEmergencia('');
                    setClaveEmergencia(generarIdempotencyKey());
                    setFechaSeleccionada(
                      new Date(
                        mesVisible.getFullYear(),
                        mesVisible.getMonth(),
                        dia,
                      ),
                    );
                  }}
                  type="button"
                >
                  <strong>{dia}</strong>
                  <span className={estilos.cupo}>
                    {(['DIA', 'NOCHE'] as const).map((franja) => {
                      const fecha = fechaLocal(
                        new Date(mesVisible.getFullYear(), mesVisible.getMonth(), dia),
                      );
                      const disponibilidad =
                        cargaDelMes.estado === 'lista'
                          ? cargaDelMes.disponibilidad.find(
                              (item) => item.fecha === fecha && item.franja === franja,
                            )
                          : undefined;
                      const etiquetaFranja = nombreFranja(franja);
                      const cupoCompleto =
                        disponibilidad !== undefined &&
                        disponibilidad.ocupado >= disponibilidad.cupo_maximo;

                      return (
                        <span
                          aria-label={
                            disponibilidad
                              ? `${etiquetaFranja}: ${disponibilidad.ocupado} de ${disponibilidad.cupo_maximo} plazas ocupadas`
                              : `${etiquetaFranja}: cupo sin datos`
                          }
                          className={estilos.cupoFranja}
                          key={franja}
                        >
                          <i
                            aria-hidden="true"
                            className={[
                              estilos.puntoFranja,
                              disponibilidad
                                ? franja === 'DIA'
                                  ? estilos.cupoDia
                                  : estilos.cupoNoche
                                : estilos.cupoSinDatos,
                            ].join(' ')}
                          />
                          {disponibilidad ? (
                            <span
                              className={
                                cupoCompleto
                                  ? estilos.cupoOcupadoCompleto
                                  : estilos.cupoOcupadoParcial
                              }
                            >
                              {disponibilidad.ocupado}
                            </span>
                          ) : null}
                          {disponibilidad ? (
                            <span className={estilos.cupoMaximo}>
                              /{disponibilidad.cupo_maximo}
                            </span>
                          ) : null}
                        </span>
                      );
                    })}
                  </span>
                </button>
              ),
            )}
          </div>
          <div className={estilos.leyenda} aria-label="Franjas de guardería">
            <span><i className={estilos.muestraDia} /> Día</span>
            <span><i className={estilos.muestraNoche} /> Noche</span>
          </div>
        </section>

        <aside className={estilos.panelDia} aria-labelledby="titulo-agenda-dia">
          <p className={estilos.antetituloPanel}>Agenda del día</p>
          <h2 id="titulo-agenda-dia">{fechaLarga}</h2>

          <section className={estilos.seccionAgenda} aria-labelledby="titulo-reservas">
            <div className={estilos.encabezadoAgenda}>
              <IconoAgenda tipo="guarderia" />
              <h3 id="titulo-reservas">Reservas de guardería</h3>
              <span
                aria-label={
                  cargaDelMes.estado === 'lista'
                    ? `${reservasDelDia.length} reservas`
                    : 'Reservas sin datos'
                }
              >
                {cargaDelMes.estado === 'lista'
                  ? reservasDelDia.length
                  : cargaDelMes.estado === 'cargando'
                    ? '…'
                    : '—'}
              </span>
            </div>
            {cargaDelMes.estado === 'cargando' ? (
              <p className={estilos.vacioAgenda} role="status">
                Cargando reservas…
              </p>
            ) : cargaDelMes.estado === 'lista' && reservasDelDia.length === 0 ? (
              <p className={estilos.vacioAgenda}>
                No hay reservas para esta fecha.
              </p>
            ) : cargaDelMes.estado === 'lista' ? (
              <ul className={estilos.listaReservas}>
                {reservasDelDia.map((reserva) => {
                  const franjas = franjasDeReservaEnFecha(
                    reserva,
                    fechaSeleccionadaISO,
                  );

                  return (
                    <li className={estilos.reservaAgenda} key={reserva.id}>
                      <Link to={`/guarderia/reservas/${reserva.id}`}>
                        Reserva #{reserva.id}
                      </Link>
                      <span>
                        {franjas.map(nombreFranja).join(' · ')}
                      </span>
                      <span>
                        {reserva.pacientes.length}{' '}
                        {reserva.pacientes.length === 1 ? 'mascota' : 'mascotas'}
                      </span>
                    </li>
                  );
                })}
              </ul>
            ) : null}
          </section>

          {esDuenio ? (
            <section
              aria-labelledby="titulo-emergencia"
              className={estilos.seccionAgenda}
            >
              <h3 id="titulo-emergencia">Plaza de emergencia</h3>
              {emergenciaAgotada ? (
                <p className={estilos.vacioAgenda}>
                  No quedan plazas de emergencia disponibles para {nombreFranja(franjaEmergencia)}.
                </p>
              ) : null}
              <Boton
                disabled={todasLasEmergenciasAgotadas || enviandoEmergencia}
                onClick={() => {
                  setEmergenciaAbierta((abierta) => !abierta);
                  setErrorEmergencia('');
                  setClaveEmergencia(generarIdempotencyKey());
                }}
                variante="secundario"
              >
                {emergenciaAbierta
                  ? 'Cerrar habilitación'
                  : 'Habilitar plaza de emergencia'}
              </Boton>
              {emergenciaAbierta ? (
                <form
                  className={estilos.formularioEmergencia}
                  onSubmit={enviarHabilitacionEmergencia}
                >
                  <p>
                    Fecha: <strong>{fechaSeleccionadaISO}</strong>
                  </p>
                  <Campo etiqueta="Franja" id="franja-emergencia">
                    <select
                      disabled={enviandoEmergencia}
                      id="franja-emergencia"
                      onChange={(evento) => {
                        setFranjaEmergencia(
                          evento.currentTarget.value === 'NOCHE' ? 'NOCHE' : 'DIA',
                        );
                        setClaveEmergencia(generarIdempotencyKey());
                        setErrorEmergencia('');
                      }}
                      value={franjaEmergencia}
                    >
                      <option value="DIA">Día</option>
                      <option value="NOCHE">Noche</option>
                    </select>
                  </Campo>
                  <Campo etiqueta="Motivo" id="motivo-emergencia">
                    <textarea
                      disabled={enviandoEmergencia}
                      id="motivo-emergencia"
                      maxLength={500}
                      onChange={(evento) => {
                        setMotivoEmergencia(evento.currentTarget.value);
                        setClaveEmergencia(generarIdempotencyKey());
                        setErrorEmergencia('');
                      }}
                      required
                      value={motivoEmergencia}
                    />
                  </Campo>
                  {errorEmergencia ? (
                    <div role="alert">{errorEmergencia}</div>
                  ) : null}
                  <Boton
                    cargando={enviandoEmergencia}
                    disabled={!motivoEmergencia.trim() || emergenciaAgotada}
                    type="submit"
                  >
                    Confirmar habilitación
                  </Boton>
                </form>
              ) : null}
            </section>
          ) : null}

          <section className={estilos.seccionAgenda} aria-labelledby="titulo-turnos">
            <div className={estilos.encabezadoAgenda}>
              <IconoAgenda tipo="clinica" />
              <h3 id="titulo-turnos">Turnos clínicos</h3>
              <span aria-label="Turnos sin datos">—</span>
            </div>
            <p className={estilos.vacioAgenda}>
              Los turnos de esta fecha aparecerán aquí.
            </p>
          </section>

          {!soloLectura ? (
            <Link
              className={estilos.botonReserva}
              to={`/guarderia/reservar?fecha=${fechaSeleccionadaISO}`}
            >
              <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M12 5v14M5 12h14" />
              </svg>
              Nueva reserva
            </Link>
          ) : null}
        </aside>
      </div>
    </section>
  );
}
