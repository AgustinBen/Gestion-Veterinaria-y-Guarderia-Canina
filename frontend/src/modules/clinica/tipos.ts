/**
 * Tipos de la agenda veterinaria y la historia clínica, alineados a
 * `backend/app/modules/clinica/schemas.py` y `models.py`.
 *
 * La UI no calcula dinero clínico: el único monto que se muestra es el costo
 * acordado con un veterinario externo y solo para el rol Dueño.
 */

export type TipoAtencion =
  | 'CONSULTA'
  | 'VACUNA'
  | 'CIRUGIA'
  | 'TRATAMIENTO'
  | 'ESTUDIO';

export type TipoTurnoMedico =
  | 'CONSULTA'
  | 'VACUNA'
  | 'CIRUGIA'
  | 'ESTUDIO'
  | 'CONTROL';

export type EstadoTurno =
  | 'PROGRAMADO'
  | 'PENDIENTE_EXTERNO'
  | 'CONFIRMADO'
  | 'ATENDIDO'
  | 'CANCELADO'
  | 'AUSENTE';

export type FranjaTurnoPersonal = 'MANANA' | 'TARDE' | 'NOCHE';

export type OrigenAtencion = 'NORMAL' | 'MIGRACION';

export type TipoEventoExterno =
  | 'CONTACTADO'
  | 'CONFIRMADO'
  | 'RECHAZADO'
  | 'REEMPLAZADO';

export type MedioEventoExterno =
  | 'TELEFONO'
  | 'WHATSAPP'
  | 'PRESENCIAL'
  | 'OTRO';

export type TipoEstudio = 'RADIOGRAFIA' | 'ECOGRAFIA' | 'ANALISIS' | 'OTRO';

export type EstadoVacuna = 'VIGENTE' | 'POR_VENCER' | 'VENCIDA';

export type VacunaNueva = {
  nombre_vacuna: string;
  lote?: string | null;
  fecha_aplicacion: string;
  proxima_dosis?: string | null;
};

export type AtencionCrear = {
  tipo: TipoAtencion;
  fecha_hora?: string | null;
  veterinario_empleado_id?: number | null;
  motivo?: string | null;
  diagnostico?: string | null;
  tratamiento?: string | null;
  observaciones?: string | null;
  cirujano_externo_id?: number | null;
  cargo_id?: number | null;
  vacuna?: VacunaNueva | null;
};

export type VacunaAplicada = {
  id: number;
  atencion_id: number;
  nombre_vacuna: string;
  lote: string | null;
  fecha_aplicacion: string;
  proxima_dosis: string | null;
};

export type AtencionResumen = {
  id: number;
  paciente_id: number;
  tipo: TipoAtencion;
  fecha_hora: string;
  veterinario_empleado_id: number;
  veterinario_nombre: string | null;
  motivo: string | null;
  diagnostico: string | null;
  tratamiento: string | null;
  observaciones: string | null;
  cirujano_externo_id: number | null;
  cirujano_externo_nombre: string | null;
  cargo_id: number | null;
  origen: OrigenAtencion;
  texto_original: string | null;
  rectifica_a_id: number | null;
  rectificada: boolean;
};

export type AtencionDetalle = AtencionResumen & {
  created_by: number;
  created_at: string;
  vacuna: VacunaAplicada | null;
};

export type LibretaVacunasItem = {
  atencion_id: number;
  nombre_vacuna: string;
  lote: string | null;
  fecha_aplicacion: string;
  proxima_dosis: string | null;
  estado: EstadoVacuna;
};

export type EstudioCrear = {
  tipo: TipoEstudio;
  fecha: string;
  descripcion: string;
  realizado_por_empleado_id: number;
  costo_centavos?: number | null;
};

export type AdjuntoResumen = {
  id: number;
  nombre_original: string;
  tipo_mime: string;
  tamano_bytes: number;
  sha256: string;
  created_by: number;
  created_at: string;
};

export type EstudioResumen = {
  id: number;
  paciente_id: number;
  atencion_id: number | null;
  tipo: TipoEstudio;
  fecha: string;
  descripcion: string;
  realizado_por_empleado_id: number;
  cargo_id: number | null;
  created_by: number;
  created_at: string;
  adjuntos: AdjuntoResumen[];
};

export type HorarioAtencion = {
  id: number;
  dia_semana: number;
  hora_desde: string;
  hora_hasta: string;
};

export type Turno = {
  id: number;
  paciente_id: number;
  tipo: TipoTurnoMedico;
  veterinario_empleado_id: number;
  inicio: string;
  fin: string;
  estado: EstadoTurno;
  motivo: string | null;
  atencion_id: number | null;
  externo_actual_id: number | null;
  cargo_id: number | null;
  created_by: number;
  created_at: string;
};

export type TurnoAtendido = Turno & {
  gasto_registrado: boolean;
};

export type TurnoCrear = {
  paciente_id: number;
  tipo: TipoTurnoMedico;
  veterinario_empleado_id: number;
  inicio: string;
  fin: string;
  motivo?: string | null;
  externo_empleado_id?: number | null;
  /** Monto a cobrar al dueño, en centavos. Se registra como cargo en Cobros. */
  monto_centavos?: number;
};

export type TurnoReprogramar = {
  inicio?: string;
  fin?: string;
  veterinario_empleado_id?: number;
};

export type EventoExterno = {
  id: number;
  turno_id: number;
  tipo: TipoEventoExterno;
  externo_empleado_id: number;
  externo_nombre: string | null;
  medio: MedioEventoExterno | null;
  nota: string | null;
  costo_acordado_centavos: number | null;
  costo_registrado: boolean;
  usuario_id: number;
  created_at: string;
};

export type AgendaDia = {
  fecha: string;
  horarios_atencion: HorarioAtencion[];
  turnos: Turno[];
};

export type ErrorAgenda = {
  codigo: string;
  mensaje: string;
};

/** Categorías visibles en la historia clínica. Se corresponden con `TipoAtencion`. */
export type CategoriaClinica = Extract<
  TipoAtencion,
  'CONSULTA' | 'VACUNA' | 'CIRUGIA' | 'TRATAMIENTO'
>;
