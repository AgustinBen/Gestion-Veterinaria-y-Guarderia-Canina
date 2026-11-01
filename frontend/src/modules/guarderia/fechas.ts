const DIAS_SEMANA = 7;

export function fechaLocal(fecha: Date): string {
  const anio = fecha.getFullYear();
  const mes = String(fecha.getMonth() + 1).padStart(2, '0');
  const dia = String(fecha.getDate()).padStart(2, '0');

  return `${anio}-${mes}-${dia}`;
}

export function desdeFechaLocal(texto: string): Date {
  const [anio, mes, dia] = texto.split('-').map(Number);

  if (
    anio === undefined ||
    mes === undefined ||
    dia === undefined ||
    !Number.isInteger(anio) ||
    !Number.isInteger(mes) ||
    !Number.isInteger(dia)
  ) {
    throw new Error('La fecha no tiene un formato válido.');
  }

  const resultado = new Date(anio, mes - 1, dia);

  if (
    resultado.getFullYear() !== anio ||
    resultado.getMonth() !== mes - 1 ||
    resultado.getDate() !== dia
  ) {
    throw new Error('La fecha indicada no existe.');
  }

  return resultado;
}

export function sumarDias(fecha: Date, dias: number): Date {
  const resultado = new Date(fecha);
  resultado.setDate(resultado.getDate() + dias);

  return resultado;
}

export function lunesDeSemana(fecha: Date): Date {
  const resultado = new Date(fecha);
  const diasDesdeLunes = (resultado.getDay() + DIAS_SEMANA - 1) % DIAS_SEMANA;
  resultado.setDate(resultado.getDate() - diasDesdeLunes);
  resultado.setHours(0, 0, 0, 0);

  return resultado;
}

export function fechasDeSemana(inicio: Date): Date[] {
  return Array.from({ length: DIAS_SEMANA }, (_, indice) =>
    sumarDias(inicio, indice),
  );
}

export function primerDiaDelMes(fecha: Date): Date {
  return new Date(fecha.getFullYear(), fecha.getMonth(), 1);
}

export function sumarMeses(fecha: Date, meses: number): Date {
  return new Date(fecha.getFullYear(), fecha.getMonth() + meses, 1);
}

export function fechasDelMes(fecha: Date): Date[] {
  const inicio = primerDiaDelMes(fecha);
  const cantidadDias = new Date(inicio.getFullYear(), inicio.getMonth() + 1, 0).getDate();

  return Array.from({ length: cantidadDias }, (_, indice) =>
    sumarDias(inicio, indice),
  );
}

export function espaciosAntesDelMes(fecha: Date): number {
  return (primerDiaDelMes(fecha).getDay() + DIAS_SEMANA - 1) % DIAS_SEMANA;
}

export function formatearFecha(fecha: Date, opciones?: Intl.DateTimeFormatOptions): string {
  return new Intl.DateTimeFormat('es-AR', opciones).format(fecha);
}

export function formatoFechaReserva(fecha: string): string {
  return formatearFecha(desdeFechaLocal(fecha), { day: '2-digit', month: '2-digit' });
}
