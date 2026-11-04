import type { Disponibilidad } from './tipos';

/**
 * RN-13: los cupos públicos son el cupo máximo menos las plazas de emergencia.
 * Las plazas ocupadas se descuentan una por una, así que cada reserva nueva
 * reduce este número. Es solo lectura de datos de la API: no crea reglas.
 */
export function cuposPublicosLibres(
  disponibilidad: Pick<
    Disponibilidad,
    'cupo_maximo' | 'plazas_emergencia' | 'ocupado'
  >,
): number {
  return Math.max(
    disponibilidad.cupo_maximo -
      disponibilidad.plazas_emergencia -
      disponibilidad.ocupado,
    0,
  );
}

/**
 * Porcentaje del cupo público desde el cual una franja se considera con
 * "últimas plazas". Es una política de presentación: no altera cupos,
 * reservas ni ninguna regla de negocio.
 */
export const UMBRAL_ULTIMAS_PLAZAS_PORCENTAJE = 25;

export type NivelDisponibilidad =
  | 'libre'
  | 'limitada'
  | 'sin-cupo'
  | 'sin-datos';

type DatosDisponibilidad = Pick<
  Disponibilidad,
  'publico' | 'disponible' | 'exceso_ocupacion'
>;

const ETIQUETAS: Record<NivelDisponibilidad, string> = {
  libre: 'Con lugar',
  limitada: 'Últimas plazas',
  'sin-cupo': 'Completo',
  'sin-datos': 'Sin datos',
};

export function etiquetaNivel(nivel: NivelDisponibilidad): string {
  return ETIQUETAS[nivel];
}

/**
 * Clasifica una franja según la disponibilidad que ya devuelve la API.
 * El umbral entra por parámetro para no fijar un porcentaje en la lógica.
 *
 * - Rojo: no queda ninguna plaza pública (`disponible <= 0`) o hay exceso.
 * - Amarillo: quedan plazas, pero dentro del porcentaje configurado.
 * - Verde: quedan plazas por encima del porcentaje configurado.
 * - Sin datos: la API no informó esa fecha/franja.
 */
export function nivelDisponibilidad(
  disponibilidad: DatosDisponibilidad | null | undefined,
  porcentajeUmbral: number = UMBRAL_ULTIMAS_PLAZAS_PORCENTAJE,
): NivelDisponibilidad {
  if (!disponibilidad) {
    return 'sin-datos';
  }

  if (disponibilidad.disponible <= 0 || disponibilidad.exceso_ocupacion > 0) {
    return 'sin-cupo';
  }

  // Sin cupo público no hay proporción que calcular; si hubiera disponibilidad
  // con cupo cero, se la trata como libre para no inventar una alarma.
  if (disponibilidad.publico <= 0) {
    return 'libre';
  }

  // Multiplicación en lugar de división: evita redondeos y divisiones por cero.
  return disponibilidad.disponible * 100 <=
    disponibilidad.publico * porcentajeUmbral
    ? 'limitada'
    : 'libre';
}
