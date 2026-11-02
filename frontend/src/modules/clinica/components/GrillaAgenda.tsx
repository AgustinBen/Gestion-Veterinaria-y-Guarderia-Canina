import { horaDeIso, formatearFechaLarga } from '../fechas';
import type {
  AgendaDia,
  EstadoTurno,
  TipoTurnoMedico,
} from '../tipos';
import estilos from '../clinica.module.css';

const ETIQUETA_TURNO: Record<TipoTurnoMedico, string> = {
  CONSULTA: 'Consulta',
  VACUNA: 'Vacuna',
  CIRUGIA: 'Cirugía',
  ESTUDIO: 'Estudio',
  CONTROL: 'Control',
};

const ETIQUETA_ESTADO: Record<EstadoTurno, string> = {
  PROGRAMADO: 'Programado',
  PENDIENTE_EXTERNO: 'Pendiente externo',
  CONFIRMADO: 'Confirmado',
  ATENDIDO: 'Atendido',
  CANCELADO: 'Cancelado',
  AUSENTE: 'Ausente',
};

const CLASE_ESTADO: Record<EstadoTurno, string> = {
  PROGRAMADO: estilos.estadoProgramado ?? '',
  PENDIENTE_EXTERNO: estilos.estadoPendiente ?? '',
  CONFIRMADO: estilos.estadoConfirmado ?? '',
  ATENDIDO: estilos.estadoAtendido ?? '',
  CANCELADO: estilos.estadoCancelado ?? '',
  AUSENTE: estilos.estadoAusente ?? '',
};

type Props = {
  dia: AgendaDia;
  nombrePaciente: (pacienteId: number) => string;
  nombreEmpleado: (empleadoId: number) => string;
  onAbrirTurno: (turnoId: number) => void;
};

export function GrillaAgenda({
  dia,
  nombrePaciente,
  nombreEmpleado,
  onAbrirTurno,
}: Props) {
  const turnos = [...dia.turnos].sort((a, b) =>
    a.inicio.localeCompare(b.inicio),
  );

  return (
    <section className={estilos.panel} aria-labelledby="agenda-dia-titulo">
      <div className={estilos.panelCabecera}>
        <div>
          <h2 className={estilos.panelTitulo} id="agenda-dia-titulo">
            Turnos del día
          </h2>
        </div>
        <span className={estilos.etiqueta}>{formatearFechaLarga(dia.fecha)}</span>
      </div>

      <div>
        {turnos.length === 0 ? (
          <p className={estilos.vacio}>No hay turnos clínicos para este día.</p>
        ) : (
          <ul className={estilos.lista}>
            {turnos.map((turno) => (
              <li key={turno.id}>
                <button
                  className={estilos.turnoClinico}
                  onClick={() => onAbrirTurno(turno.id)}
                  type="button"
                >
                  <span className={estilos.turnoHora}>
                    {horaDeIso(turno.inicio)}
                  </span>
                  <span className={estilos.turnoInfo}>
                    <strong>{nombrePaciente(turno.paciente_id)}</strong>
                    <span>
                      {ETIQUETA_TURNO[turno.tipo]} ·{' '}
                      {nombreEmpleado(turno.veterinario_empleado_id)}
                    </span>
                  </span>
                  <span
                    className={`${estilos.estado} ${CLASE_ESTADO[turno.estado]}`.trim()}
                  >
                    {ETIQUETA_ESTADO[turno.estado]}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
