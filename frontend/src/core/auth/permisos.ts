export const ROLES = ['DUENIO', 'PERSONAL', 'VETERINARIO'] as const;

export type Rol = (typeof ROLES)[number];

export type SeccionId =
  | 'panel'
  | 'padron'
  | 'calendario'
  | 'nueva-reserva'
  | 'turnos'
  | 'historia-clinica'
  | 'cobros'
  | 'deudores'
  | 'migracion'
  | 'crear-cuenta';

export type NivelAcceso = 'lectura' | 'escritura';

export type Seccion = {
  id: SeccionId;
  etiqueta: string;
  etiquetaCorta: string;
  ruta: string;
};

export const SECCIONES: readonly Seccion[] = [
  { id: 'panel', etiqueta: 'Panel', etiquetaCorta: 'Panel', ruta: '/panel' },
  {
    id: 'padron',
    etiqueta: 'Dueños y mascotas',
    etiquetaCorta: 'Dueños',
    ruta: '/padron',
  },
  {
    id: 'calendario',
    etiqueta: 'Calendario',
    etiquetaCorta: 'Calendario',
    ruta: '/guarderia/calendario',
  },
  {
    id: 'nueva-reserva',
    etiqueta: 'Nueva reserva',
    etiquetaCorta: 'Reserva',
    ruta: '/guarderia/nueva',
  },
  { id: 'turnos', etiqueta: 'Turnos', etiquetaCorta: 'Turnos', ruta: '/turnos' },
  {
    id: 'historia-clinica',
    etiqueta: 'Historia clínica',
    etiquetaCorta: 'Historia',
    ruta: '/historia-clinica',
  },
  { id: 'cobros', etiqueta: 'Cobros', etiquetaCorta: 'Cobros', ruta: '/cobros' },
  {
    id: 'deudores',
    etiqueta: 'Deudores',
    etiquetaCorta: 'Deudores',
    ruta: '/cobros/deudores',
  },
  {
    id: 'migracion',
    etiqueta: 'Migración',
    etiquetaCorta: 'Migración',
    ruta: '/migracion',
  },
  {
    id: 'crear-cuenta',
    etiqueta: 'Crear cuenta',
    etiquetaCorta: 'Crear cuenta',
    ruta: '/identidad/crear-cuenta',
  },
];

/**
 * Matriz de acceso rol × sección (docs/reglas-de-negocio.md §3 y alcance de T-09).
 * `lectura` habilita ver; `escritura` habilita ver y operar. `null` = sin acceso
 * (default denegar). Ningún componente compara roles a mano.
 */
const PERMISOS_POR_ROL: Readonly<Record<Rol, Readonly<Record<SeccionId, NivelAcceso | null>>>> = {
  DUENIO: {
    panel: 'escritura',
    padron: 'escritura',
    calendario: 'escritura',
    'nueva-reserva': 'escritura',
    turnos: 'escritura',
    'historia-clinica': 'escritura',
    cobros: 'escritura',
    deudores: 'escritura',
    migracion: 'escritura',
    'crear-cuenta': 'escritura',
  },
  PERSONAL: {
    panel: null,
    padron: 'escritura',
    calendario: 'escritura',
    'nueva-reserva': 'escritura',
    turnos: 'escritura',
    // La matriz deja la lectura como PENDIENTE del cliente; el ticket T-09
    // enumera las secciones de PERSONAL sin historia clínica.
    'historia-clinica': null,
    cobros: 'escritura',
    // El listado global de deudores es información financiera: solo DUENIO.
    // Personal sigue viendo la deuda del cliente dentro de su cuenta.
    deudores: null,
    migracion: null,
    'crear-cuenta': null,
  },
  VETERINARIO: {
    panel: null,
    padron: 'lectura',
    calendario: 'lectura',
    'nueva-reserva': null,
    turnos: 'escritura',
    'historia-clinica': 'escritura',
    cobros: null,
    deudores: null,
    migracion: null,
    'crear-cuenta': null,
  },
};

/**
 * Orden y contenido de la barra de navegación por rol. Es solo presentación:
 * no otorga permisos, esos viven en PERMISOS_POR_ROL.
 *
 * Fuera del menú pero accesibles por URL (los permisos siguen vigentes):
 * - Migración: tarea administrativa de una sola vez, solo DUENIO.
 * - Turnos para DUENIO: la agenda la operan recepción y veterinaria.
 *
 * Deudores no figura en el menú de PERSONAL y tampoco tiene permiso: el
 * listado global es información financiera (solo DUENIO). La deuda de un
 * cliente se sigue viendo desde su cuenta de cobros.
 */
const MENU_POR_ROL: Readonly<Record<Rol, readonly SeccionId[]>> = {
  DUENIO: [
    'panel',
    'padron',
    'calendario',
    'nueva-reserva',
    'historia-clinica',
    'cobros',
    'deudores',
    'crear-cuenta',
  ],
  PERSONAL: ['padron', 'calendario', 'nueva-reserva', 'cobros', 'turnos'],
  VETERINARIO: ['padron', 'calendario', 'turnos', 'historia-clinica'],
};

const ETIQUETAS_ROL: Readonly<Record<Rol, string>> = {
  DUENIO: 'Dueño',
  PERSONAL: 'Personal',
  VETERINARIO: 'Veterinario',
};

const SECCIONES_POR_ID = new Map(SECCIONES.map((seccion) => [seccion.id, seccion]));

export function esRol(valor: unknown): valor is Rol {
  return typeof valor === 'string' && (ROLES as readonly string[]).includes(valor);
}

export function etiquetaRol(rol: Rol): string {
  return ETIQUETAS_ROL[rol];
}

export function nivelDeAcceso(rol: Rol, seccion: SeccionId): NivelAcceso | null {
  return PERMISOS_POR_ROL[rol][seccion];
}

export function puedeAcceder(
  rol: Rol,
  seccion: SeccionId,
  nivelRequerido: NivelAcceso = 'lectura',
): boolean {
  const nivel = nivelDeAcceso(rol, seccion);

  if (nivel === null) {
    return false;
  }

  return nivelRequerido === 'lectura' || nivel === 'escritura';
}

/** Secciones que este rol ve en el menú, en orden. */
export function seccionesVisibles(rol: Rol): readonly Seccion[] {
  return MENU_POR_ROL[rol].flatMap((id) => {
    const seccion = SECCIONES_POR_ID.get(id);
    return seccion ? [seccion] : [];
  });
}

/** Sección correspondiente a una ruta, eligiendo la coincidencia más específica. */
export function seccionDeRuta(pathname: string): Seccion | undefined {
  let encontrada: Seccion | undefined;

  for (const seccion of SECCIONES) {
    const coincide =
      pathname === seccion.ruta || pathname.startsWith(`${seccion.ruta}/`);

    if (coincide && (!encontrada || seccion.ruta.length > encontrada.ruta.length)) {
      encontrada = seccion;
    }
  }

  return encontrada;
}

export function rutaInicial(rol: Rol): string {
  return seccionesVisibles(rol)[0]?.ruta ?? '/sin-acceso';
}
