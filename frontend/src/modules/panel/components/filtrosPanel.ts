import type { FiltrosPanel, PeriodoId } from '../tipos';

export const PERIODOS: readonly { id: PeriodoId; etiqueta: string }[] = [
  { id: 'hoy', etiqueta: 'Hoy' },
  { id: 'semana', etiqueta: 'Esta semana' },
  { id: 'mes', etiqueta: 'Este mes' },
  { id: 'mes-anterior', etiqueta: 'Mes anterior' },
  { id: 'personalizado', etiqueta: 'Personalizado' },
];

export function fechaIsoLocal(fecha: Date): string {
  const mes = String(fecha.getMonth() + 1).padStart(2, '0');
  const dia = String(fecha.getDate()).padStart(2, '0');

  return `${fecha.getFullYear()}-${mes}-${dia}`;
}

function sumarDias(fecha: Date, dias: number): Date {
  const copia = new Date(fecha);
  copia.setDate(copia.getDate() + dias);
  return copia;
}

export function calcularRango(
  periodo: PeriodoId,
  hoy: Date = new Date(),
): { desde: string; hasta: string } {
  if (periodo === 'hoy') {
    return { desde: fechaIsoLocal(hoy), hasta: fechaIsoLocal(hoy) };
  }

  if (periodo === 'semana') {
    const dia = hoy.getDay();
    const desde = sumarDias(hoy, dia === 0 ? -6 : 1 - dia);
    return { desde: fechaIsoLocal(desde), hasta: fechaIsoLocal(hoy) };
  }

  if (periodo === 'mes-anterior') {
    const desde = new Date(hoy.getFullYear(), hoy.getMonth() - 1, 1);
    const hasta = new Date(hoy.getFullYear(), hoy.getMonth(), 0);
    return { desde: fechaIsoLocal(desde), hasta: fechaIsoLocal(hasta) };
  }

  const desde = new Date(hoy.getFullYear(), hoy.getMonth(), 1);
  return { desde: fechaIsoLocal(desde), hasta: fechaIsoLocal(hoy) };
}

function esPeriodo(valor: string | null): valor is PeriodoId {
  return PERIODOS.some((periodo) => periodo.id === valor);
}

export function leerFiltros(
  params: URLSearchParams,
  hoy: Date = new Date(),
): FiltrosPanel {
  const periodo = params.get('periodo');
  const periodoValido = esPeriodo(periodo) ? periodo : 'mes';
  const rango = calcularRango(periodoValido, hoy);

  return {
    periodo: periodoValido,
    desde:
      periodoValido === 'personalizado'
        ? params.get('desde') ?? rango.desde
        : rango.desde,
    hasta:
      periodoValido === 'personalizado'
        ? params.get('hasta') ?? rango.hasta
        : rango.hasta,
  };
}

export function parametrosDeFiltros(filtros: FiltrosPanel): URLSearchParams {
  const params = new URLSearchParams();

  params.set('periodo', filtros.periodo);
  params.set('desde', filtros.desde);
  params.set('hasta', filtros.hasta);

  return params;
}
