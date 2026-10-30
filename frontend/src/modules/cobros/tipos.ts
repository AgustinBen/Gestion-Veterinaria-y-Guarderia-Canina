/**
 * Tipos de cobros alineados a los schemas del backend
 * (`backend/app/modules/cobros/schemas.py`). Todo el dinero son centavos
 * enteros; nunca se modela saldo ni deuda como dato editable.
 */

export type MedioPago = {
  id: number;
  codigo: string;
  nombre: string;
  activo: boolean;
};

/** Respuesta mínima de GET /api/personas?q= usada para buscar al cliente. */
export type PersonaBusqueda = {
  id: number;
  nombre: string;
  apellido: string;
  dni: string | null;
  dni_pendiente: boolean;
  telefonos: string[];
};

export type CargoDetalle = {
  id: number;
  persona_id: number;
  paciente_id: number | null;
  concepto: string;
  total_inicial: number;
  origen: string;
  referencia_tipo: string | null;
  referencia_id: number | null;
  creado_por: number;
  created_at: string;
  total_vigente: number;
  total_pagado: number;
  saldo: number;
};

export type Pago = {
  id: number;
  cargo_id: number;
  monto: number;
  tipo: string;
  pago_revertido_id: number | null;
  medio_pago_id: number;
  es_sena: boolean;
  fecha: string;
  usuario_id: number;
  empleado_id: number | null;
  clave_idempotencia: string | null;
  created_at: string;
};

export type CargoCuenta = {
  cargo: CargoDetalle;
  pagos: Pago[];
};

export type CuentaCliente = {
  persona_id: number;
  saldo_total: number;
  cargos: CargoCuenta[];
};

export type Deudor = {
  persona: {
    id: number;
    nombre: string;
    apellido: string;
    telefono_principal: string | null;
  };
  saldo_total_centavos: number;
  cantidad_cargos_pendientes: number;
  deuda_mas_antigua: string;
  saldo_migracion_centavos: number;
};

export type ResumenDeuda = {
  debe: boolean;
  saldo_total_centavos: number;
  cargos_pendientes: number;
  deuda_mas_antigua: string | null;
  incluye_migracion: boolean;
};

export type PagoNuevo = {
  monto_centavos: number;
  medio: string;
  es_sena: boolean;
};

export type AjusteNuevo = {
  nuevo_total_centavos: number;
  motivo: string;
};

export type AjustePrecio = {
  id: number;
  cargo_id: number;
  precio_anterior: number;
  precio_nuevo: number;
  motivo: string;
  usuario_id: number;
  created_at: string;
};

export type OrdenDeudores = 'monto' | 'antiguedad';

export type OpcionesDeudores = {
  orden?: OrdenDeudores;
  soloMigracion?: boolean;
  limite?: number;
  offset?: number;
  signal?: AbortSignal;
};

export type OpcionesIdempotentes = {
  idempotencyKey: string;
  signal?: AbortSignal;
};
