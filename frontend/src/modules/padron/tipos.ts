/**
 * Tipos del padrón alineados a los schemas de T-12
 * (`backend/app/modules/padron/schemas.py`). No se modela nada de T-13.
 */

export type Especie = {
  id: number;
  nombre: string;
};

export type Raza = {
  id: number;
  nombre: string;
  especie_id: number;
};

export type Tamanio = {
  id: number;
  nombre: string;
};

export type Domicilio = {
  id: number;
  calle: string | null;
  numero: number | null;
  piso: string | null;
  departamento: string | null;
  localidad: string | null;
  codigo_postal: string | null;
  referencia: string | null;
};

export type DomicilioNuevo = {
  calle?: string | null;
  numero?: number | null;
  piso?: string | null;
  departamento?: string | null;
  localidad?: string | null;
  codigo_postal?: string | null;
  referencia?: string | null;
};

export type PacienteResumen = {
  id: number;
  nombre: string;
  especie_id: number;
  especie_nombre: string;
  raza_id: number | null;
  raza_nombre: string | null;
  activo: boolean;
};

export type PersonaResumen = {
  id: number;
  nombre: string;
  apellido: string;
  dni: string | null;
  dni_pendiente: boolean;
  telefonos: string[];
};

export type PersonaDetalle = PersonaResumen & {
  domicilio: Domicilio | null;
  creado_en: string;
  duplicado_confirmado: boolean;
  mascotas: PacienteResumen[];
};

export type PacienteDetalle = {
  id: number;
  nombre: string;
  especie_id: number;
  especie_nombre: string;
  raza_id: number | null;
  raza_nombre: string | null;
  tamanio_id: number | null;
  tamanio_nombre: string | null;
  peso_kg: string | number | null;
  fecha_nacimiento_aprox: string | null;
  castrado: boolean | null;
  activo: boolean;
  edad_anios: number | null;
  edad_meses: number | null;
};

export type TitularVigente = {
  persona_id: number;
  nombre: string;
  apellido: string;
  tipo: string;
  principal: boolean;
  desde: string;
};

export type CoincidenciaDuplicado = {
  persona: PersonaResumen;
  motivo: string;
  mascotas: string[];
};

export type PersonaNueva = {
  nombre: string;
  apellido: string;
  dni: string;
  domicilio?: DomicilioNuevo | null;
  telefonos: string[];
  confirmar_duplicado?: boolean;
};

export type PersonaActualizar = Partial<Omit<PersonaNueva, 'confirmar_duplicado'>> & {
  confirmar_duplicado?: boolean;
};

export type PacienteNuevo = {
  nombre: string;
  especie_id: number;
  raza_id?: number | null;
  tamanio_id?: number | null;
  peso_kg?: string | null;
  fecha_nacimiento_aprox?: string | null;
  castrado?: boolean | null;
  titular_persona_id: number;
};

export type PacienteActualizar = Partial<Omit<PacienteNuevo, 'titular_persona_id'>>;

export type RazaNueva = {
  nombre: string;
  especie_id: number;
};

export type ErrorDniDuplicado = {
  codigo: 'DNI_DUPLICADO';
  persona: PersonaResumen;
};

export type ErrorPosibleDuplicado = {
  codigo: 'POSIBLE_DUPLICADO';
  coincidencias: CoincidenciaDuplicado[];
};

export type ErrorDuplicado = ErrorDniDuplicado | ErrorPosibleDuplicado;
