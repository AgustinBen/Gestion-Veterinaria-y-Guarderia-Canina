import { useState } from 'react';
import { Link } from 'react-router-dom';

import { useAuth } from '../../../core/auth/contexto';
import { puedeAcceder } from '../../../core/auth/permisos';
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

export function Calendario() {
  const [fechaSeleccionada, setFechaSeleccionada] = useState(() => new Date());
  const { sesion } = useAuth();
  const soloLectura = sesion
    ? !puedeAcceder(sesion.rol, 'calendario', 'escritura')
    : false;
  const mesVisible = primerDiaDelMes(fechaSeleccionada);
  const dias = diasDelMes(mesVisible);
  const fechaLarga = `${fechaSeleccionada.getDate()} de ${nombreMes(fechaSeleccionada, {
    month: 'long',
  })}`;

  function cambiarMes(desplazamiento: number) {
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
                  onClick={() =>
                    setFechaSeleccionada(
                      new Date(
                        mesVisible.getFullYear(),
                        mesVisible.getMonth(),
                        dia,
                      ),
                    )
                  }
                  type="button"
                >
                  <strong>{dia}</strong>
                  <span aria-label="Cupo sin datos" className={estilos.cupo}>
                    —/—
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
              <span aria-label="Reservas sin datos">—</span>
            </div>
            <p className={estilos.vacioAgenda}>
              Las reservas de esta fecha aparecerán aquí.
            </p>
          </section>

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
            <Link className={estilos.botonReserva} to="/guarderia/nueva">
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
