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
