import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { useAuth } from '../../../core/auth/contexto';
import { Alerta } from '../../../core/components/ui/Alerta';
import { Boton } from '../../../core/components/ui/Boton';
import {
  listarEmpleados,
  listarPacientes,
  obtenerPaciente,
} from '../../padron/api';
import type { EmpleadoDetalle, PacienteResumen } from '../../padron/tipos';
import { listarIdsVeterinarios, mensajeDeError, obtenerAgenda } from '../api';
import { GrillaAgenda } from '../components/GrillaAgenda';
import {
  diasDeSemana,
  fechaLocal,
  desdeFechaLocal,
  formatearFechaLarga,
  nombreDiaCorto,
  numeroDia,
} from '../fechas';
import { puedeCrearTurnos } from '../permisos';
import type { AgendaDia } from '../tipos';
import estilos from '../clinica.module.css';

const MAX_PACIENTES = 100;

type Estado = 'cargando' | 'listo' | 'error';
type Vista = 'dia' | 'semana';

export function Turnos() {
  const { sesion } = useAuth();
  const navegar = useNavigate();
  const [vista, setVista] = useState<Vista>('dia');
  const [fecha, setFecha] = useState(fechaLocal(new Date()));
  const [veterinarioId, setVeterinarioId] = useState('');
  const [agendas, setAgendas] = useState<AgendaDia[]>([]);
  const [pacientes, setPacientes] = useState<PacienteResumen[]>([]);
  const [empleados, setEmpleados] = useState<EmpleadoDetalle[]>([]);
  const [idsVeterinarios, setIdsVeterinarios] = useState<number[]>([]);
  const [pacientesExtra, setPacientesExtra] = useState<Map<number, string>>(
    new Map(),
  );
  const pacientesExtraRef = useRef<Map<number, string>>(new Map());
  const [estado, setEstado] = useState<Estado>('cargando');
  const [error, setError] = useState('');
  const [intento, setIntento] = useState(0);

  const fechaBase = /^\d{4}-\d{2}-\d{2}$/.test(fecha)
    ? fecha
    : fechaLocal(new Date());
  const diasSemana = useMemo(
    () => diasDeSemana(desdeFechaLocal(fechaBase)),
    [fechaBase],
  );

  useEffect(() => {
    const controlador = new AbortController();
    let activo = true;

    async function cargar() {
      setEstado('cargando');
      setError('');

      const desde = vista === 'semana' ? (diasSemana[0] ?? fechaBase) : fechaBase;
      const hasta =
        vista === 'semana' ? (diasSemana[6] ?? fechaBase) : fechaBase;

      try {
        const [
          datosAgenda,
          datosPacientes,
          datosEmpleados,
          datosIdsVeterinarios,
        ] =
          await Promise.all([
            obtenerAgenda({
              desde,
              hasta,
              veterinarioId:
                veterinarioId === '' ? undefined : Number(veterinarioId),
              signal: controlador.signal,
            }),
            listarPacientes({
              limite: MAX_PACIENTES,
              signal: controlador.signal,
            }),
            listarEmpleados({ signal: controlador.signal }),
            listarIdsVeterinarios({ signal: controlador.signal }),
          ]);

        if (activo) {
          setAgendas(datosAgenda);
          setPacientes(datosPacientes);
          setEmpleados(datosEmpleados);
          setIdsVeterinarios(datosIdsVeterinarios);
          setEstado('listo');
        }
      } catch (fallo) {
        if (!activo || controlador.signal.aborted) {
          return;
        }

        setError(mensajeDeError(fallo));
        setEstado('error');
      }
    }

    void cargar();

    return () => {
      activo = false;
      controlador.abort();
    };
  }, [fechaBase, vista, veterinarioId, intento, diasSemana]);

  useEffect(() => {
    const faltantes = new Set<number>();

    for (const agenda of agendas) {
      for (const turno of agenda.turnos) {
        if (
          !pacientes.some((paciente) => paciente.id === turno.paciente_id) &&
          !pacientesExtraRef.current.has(turno.paciente_id)
        ) {
          faltantes.add(turno.paciente_id);
        }
      }
    }

    if (faltantes.size === 0) {
      return;
    }

    const controlador = new AbortController();
    let activo = true;

    async function cargarNombres() {
      const datos = await Promise.all(
        [...faltantes].map(async (pacienteId) => {
          try {
            return await obtenerPaciente(pacienteId, {
              signal: controlador.signal,
            });
          } catch {
            return null;
          }
        }),
      );

      if (!activo || controlador.signal.aborted) {
        return;
      }

      setPacientesExtra((actuales) => {
        const copia = new Map(actuales);
        let cambio = false;

        for (const paciente of datos) {
          if (paciente && !copia.has(paciente.id)) {
            copia.set(paciente.id, paciente.nombre);
            pacientesExtraRef.current.set(paciente.id, paciente.nombre);
            cambio = true;
          }
        }

        return cambio ? copia : actuales;
      });
    }

    void cargarNombres();

    return () => {
      activo = false;
      controlador.abort();
    };
  }, [agendas, pacientes]);

  const nombrePaciente = useMemo(() => {
    const mapa = new Map(pacientes.map((paciente) => [paciente.id, paciente.nombre]));

    for (const [pacienteId, nombre] of pacientesExtra) {
      mapa.set(pacienteId, nombre);
    }

    return (pacienteId: number) => mapa.get(pacienteId) ?? `Mascota #${pacienteId}`;
  }, [pacientes, pacientesExtra]);

  const nombreEmpleado = useMemo(() => {
    const mapa = new Map(
      empleados.map((empleado) => [
        empleado.persona_id,
        `${empleado.nombre} ${empleado.apellido}`.trim(),
      ]),
    );

    return (empleadoId: number) =>
      mapa.get(empleadoId) ?? `Empleado #${empleadoId}`;
  }, [empleados]);

  const idsDeVeterinarios = useMemo(
    () => new Set(idsVeterinarios),
    [idsVeterinarios],
  );
  const veterinarios = empleados.filter(
    (empleado) => idsDeVeterinarios.has(empleado.persona_id) && empleado.activo,
  );
  const dia = agendas.find((agenda) => agenda.fecha === fechaBase) ?? null;
  const esHoy = fechaBase === fechaLocal(new Date());
  const hayTurnosSemana = agendas.some((agenda) => agenda.turnos.length > 0);
  const puedeCrear = puedeCrearTurnos(sesion?.rol ?? null);

  return (
    <section className={estilos.pagina} aria-labelledby="titulo-turnos">
      <header className={`${estilos.cabecera} ${estilos.cabeceraTurnos}`}>
        <div className={estilos.introduccion}>
          <p className={estilos.antetitulo}>Agenda veterinaria</p>
          <h1 className={estilos.titulo} id="titulo-turnos">
            Turnos
          </h1>
          <p className={estilos.subtitulo}>
            {puedeCrear
              ? 'Agenda veterinaria de la clínica.'
              : 'Tus turnos asignados.'}
          </p>
        </div>
        {puedeCrear ? (
          <div className={estilos.acciones}>
            <Link className={estilos.boton} to={`/turnos/nueva?fecha=${fechaBase}`}>
              Nuevo turno
            </Link>
          </div>
        ) : null}
      </header>

      <section className={estilos.panel} aria-label="Controles de la agenda">
        <div className={estilos.barra}>
          <Boton
            onClick={() => setVista('dia')}
            variante={vista === 'dia' ? 'primario' : 'secundario'}
          >
            Día
          </Boton>
          <Boton
            onClick={() => setVista('semana')}
            variante={vista === 'semana' ? 'primario' : 'secundario'}
          >
            Semana
          </Boton>
        </div>

        <div className={estilos.barra}>
          <label className={estilos.campoAncho} htmlFor="agenda-fecha">
            Fecha
            <input
              id="agenda-fecha"
              onChange={(evento) => setFecha(evento.target.value)}
              type="date"
              value={fecha}
            />
          </label>

          {puedeCrear ? (
            <label className={estilos.campoAncho} htmlFor="agenda-veterinario">
              Veterinario
              <select
                id="agenda-veterinario"
                onChange={(evento) => setVeterinarioId(evento.target.value)}
                value={veterinarioId}
              >
                <option value="">Todos</option>
                {veterinarios.map((empleado) => (
                  <option key={empleado.persona_id} value={empleado.persona_id}>
                    {empleado.nombre} {empleado.apellido}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
        </div>
      </section>

      {vista === 'semana' ? (
        <section className={estilos.panel} aria-label="Semana de la agenda">
          <div className={estilos.panelCabecera}>
            <h2 className={estilos.panelTitulo}>Semana</h2>
            <span className={estilos.etiqueta}>
              {formatearFechaLarga(diasSemana[0] ?? fechaBase)} —{' '}
              {formatearFechaLarga(diasSemana[6] ?? fechaBase)}
            </span>
          </div>

          <div className={estilos.semana}>
            {diasSemana.map((diaSemana) => {
              const agendaDia = agendas.find(
                (agenda) => agenda.fecha === diaSemana,
              );
              const cantidad = agendaDia?.turnos.length ?? 0;

              return (
                <button
                  aria-pressed={fechaBase === diaSemana}
                  className={`${estilos.diaSemanaBoton} ${
                    fechaBase === diaSemana ? estilos.diaSemanaActivo : ''
                  }`.trim()}
                  key={diaSemana}
                  onClick={() => setFecha(diaSemana)}
                  type="button"
                >
                  <span className={estilos.diaSemanaNombre}>
                    {nombreDiaCorto(diaSemana)}
                  </span>
                  <span className={estilos.diaSemanaNumero}>
                    {numeroDia(diaSemana)}
                  </span>
                  <span className={estilos.diaSemanaConteo}>{cantidad}</span>
                </button>
              );
            })}
          </div>
        </section>
      ) : null}

      {estado === 'cargando' ? (
        <section className={estilos.panel}>
          <p className={estilos.cargando}>Cargando agenda…</p>
        </section>
      ) : estado === 'error' ? (
        <section className={estilos.panel}>
          <Alerta
            acciones={
              <Boton
                onClick={() => setIntento((actual) => actual + 1)}
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
        </section>
      ) : (
        <>
          {dia && dia.turnos.length > 0 ? (
            <GrillaAgenda
              dia={dia}
              nombreEmpleado={nombreEmpleado}
              nombrePaciente={nombrePaciente}
              onAbrirTurno={(turnoId) => navegar(`/turnos/${turnoId}`)}
            />
          ) : (
            <section className={estilos.panel}>
              <p className={estilos.vacio}>
                {vista === 'semana' && !hayTurnosSemana
                  ? 'No hay turnos en la semana.'
                  : esHoy
                    ? 'No hay turnos el día de hoy.'
                    : 'No hay turnos para el día seleccionado.'}
              </p>
            </section>
          )}
        </>
      )}
    </section>
  );
}
