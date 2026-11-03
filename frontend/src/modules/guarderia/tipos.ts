export type Franja = 'DIA' | 'NOCHE';

export type EstadoReserva =
  | 'PENDIENTE_SENA'
  | 'CONFIRMADA'
  | 'EN_CURSO'
  | 'FINALIZADA'
  | 'CANCELADA'
  | 'AUSENTE';

export type Disponibilidad = {
  fecha: string;
  franja: Franja;
  cupo_maximo: number;
  plazas_emergencia: number;
  habilitadas: number;
  publico: number;
  ocupado: number;
  disponible: number;
  exceso_ocupacion: number;
};

export type SobreocupacionCupo = {
  fecha: string;
  franja: Franja;
  publico: number;
  ocupado: number;
  exceso: number;
};

export type ConfiguracionCupo = {
  cupo_maximo: number;
  cupo_minimo: number;
  cupo_maximo_permitido: number;
  fecha_consultada: string | null;
  cupo_fecha: number | null;
  fecha_es_excepcion: boolean;
  sobreocupaciones: SobreocupacionCupo[];
};

export type HabilitacionEmergenciaCrear = {
  fecha: string;
  franja: Franja;
  motivo: string;
};

export type CuidadoExtraAnimal = {
  paciente_id: number;
  cuidados_extras: boolean;
  tipo_cuidado?: string | null;
};

export type ReservaCrear = {
  tutor_persona_id: number;
  paciente_ids: number[];
  desde_fecha: string;
  desde_franja: Franja;
  hasta_fecha: string;
  hasta_franja: Franja;
  cuidados_extras: CuidadoExtraAnimal[];
  total_centavos: number;
};

export type ReservaSenaCrear = {
  monto_centavos: number;
  medio: string;
};

export type ReservaPaciente = {
  paciente_id: number;
  cuidados_extras: boolean;
  tipo_cuidado: string | null;
};

export type Reserva = {
  id: number;
  tutor_persona_id: number;
  desde_fecha: string;
  desde_franja: Franja;
  hasta_fecha: string;
  hasta_franja: Franja;
  estado: EstadoReserva;
  cargo_id: number | null;
  total_centavos: number | null;
  sena_centavos: number;
  pacientes: ReservaPaciente[];
  created_at: string;
};

export type FranjaSinLugar = {
  fecha: string;
  franja: Franja;
  necesita: number;
  disponible: number;
};

export type OcupacionExistente = {
  paciente_id: number;
  fecha: string;
  franja: Franja;
};

export type ErrorCupoReserva = {
  codigo: 'SIN_CUPO';
  franjas_sin_lugar: FranjaSinLugar[];
  ocupaciones_existentes: OcupacionExistente[];
};

export type ErrorMascotaReservada = {
  codigo: 'YA_RESERVADO';
  franjas_sin_lugar: FranjaSinLugar[];
  ocupaciones_existentes: OcupacionExistente[];
};

export type ErrorReserva = ErrorCupoReserva | ErrorMascotaReservada;

export type OpcionesLectura = {
  signal?: AbortSignal;
};

export type OpcionesIdempotentes = OpcionesLectura & {
  idempotencyKey: string;
};

/** Turno clínico tal como lo expone `GET /api/turnos` (solo lectura aquí). */
export type TurnoClinico = {
  id: number;
  paciente_id: number;
  tipo: 'CONSULTA' | 'VACUNA' | 'CIRUGIA' | 'ESTUDIO' | 'CONTROL';
  veterinario_empleado_id: number;
  inicio: string;
  fin: string;
  estado:
    | 'PROGRAMADO'
    | 'PENDIENTE_EXTERNO'
    | 'CONFIRMADO'
    | 'ATENDIDO'
    | 'CANCELADO'
    | 'AUSENTE';
};
