/**
 * Tipos del panel financiero del Dueño (T-46, T-22 y T-38).
 *
 * Todo el dinero viaja en centavos enteros. Las deudas se muestran aparte de
 * la rentabilidad (RN-40).
 */

export type PeriodoId =
  | 'hoy'
  | 'semana'
  | 'mes'
  | 'mes-anterior'
  | 'personalizado';

export type FiltrosPanel = {
  periodo: PeriodoId;
  desde: string;
  hasta: string;
};

export type CalidadDatos = {
  cargos_otro: number;
  cargos_migrados: number;
  total_cargos: number;
};

export type ResumenPanel = {
  desde: string;
  hasta: string;
  ingresos_centavos: number;
  ingresos_migracion_centavos: number;
  egresos_operativos_centavos: number;
  egresos_operativos_sin_asignar_centavos: number;
  gastos_externos_centavos: number;
  rentabilidad_neta_centavos: number | null;
  rentabilidad_neta_motivo: string | null;
  calidad_datos: CalidadDatos;
};

export type IngresoHistorial = {
  id: number;
  cargo_id: number;
  monto_centavos: number;
  tipo: string;
  estado: string;
  fecha: string;
  medio: string;
  medio_pago_id: number;
  es_sena: boolean;
  concepto: string;
  tipo_servicio: string;
  origen: string;
  usuario_id: number;
  empleado_id: number | null;
  motivo: string | null;
  created_at: string;
};

export type MayorDeudor = {
  persona_id: number;
  nombre: string;
  apellido: string;
  saldo_total_centavos: number;
  migracion_centavos: number;
  cantidad_cargos_pendientes: number;
  deuda_mas_antigua: string;
};

export type DeudasPanel = {
  total_adeudado_centavos: number;
  cantidad_clientes: number;
  deuda_migracion_centavos: number;
  mayores_deudores: MayorDeudor[];
};

export type ServicioCliente = {
  cargo_id: number;
  tipo_servicio: string;
  concepto: string;
  total_centavos: number;
  pagado_centavos: number;
  saldo_centavos: number;
  ajustes: number;
};

export type DetalleCliente = {
  persona_id: number;
  nombre: string;
  apellido: string;
  servicios: ServicioCliente[];
};

export type CategoriaEgreso = {
  id: number;
  nombre: string;
  activa: boolean;
};

export type Egreso = {
  id: number;
  fecha: string;
  monto_centavos: number;
  categoria_id: number;
  categoria_nombre: string;
  descripcion: string;
  medio_pago_id: number | null;
  registrado_por: number;
  created_at: string;
  anulado_en: string | null;
  anulado_por: number | null;
  motivo_anulacion: string | null;
};

export type EgresoNuevo = {
  fecha: string;
  monto_centavos: number;
  categoria_id: number;
  descripcion: string;
  medio_pago_id?: number | null;
};

export type GastoExterno = {
  id: number;
  empleado_id: number | null;
  empleado_nombre: string;
  descripcion: string;
  monto_centavos: number;
  fecha: string;
  cargo_id: number | null;
  pago_id: number | null;
  registrado_por: number;
  created_at: string;
  anulado_en: string | null;
  anulado_por: number | null;
  motivo_anulacion: string | null;
};

export type GastoExternoNuevo = {
  descripcion: string;
  monto_centavos: number;
  fecha: string;
};

export type ListaGastos = {
  items: GastoExterno[];
  total_centavos: number;
};

export type OpcionesIdempotentes = {
  idempotencyKey: string;
  signal?: AbortSignal;
};
