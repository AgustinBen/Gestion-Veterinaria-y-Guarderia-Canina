const FORMATO_FECHA_LARGA = new Intl.DateTimeFormat('es-AR', {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
});

const FORMATO_FECHA_CORTA = new Intl.DateTimeFormat('es-AR', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
});

const DIAS_CORTOS = ['Lu', 'Ma', 'Mi', 'Ju', 'Vi', 'Sá', 'Do'];

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

  return new Date(anio, mes - 1, dia);
}

export function sumarDias(fecha: Date, dias: number): Date {
  const resultado = new Date(fecha);
  resultado.setDate(resultado.getDate() + dias);

  return resultado;
}

/** Lunes de la semana que contiene la fecha. */
export function inicioDeSemana(fecha: Date): Date {
  const dia = fecha.getDay();
  const desplazamiento = dia === 0 ? -6 : 1 - dia;

  return sumarDias(fecha, desplazamiento);
}

/** Los siete días de la semana desde el lunes. */
export function diasDeSemana(fecha: Date): string[] {
  const lunes = inicioDeSemana(fecha);

  return Array.from({ length: 7 }, (_, indice) =>
    fechaLocal(sumarDias(lunes, indice)),
  );
}

export function formatearFechaLarga(fecha: string): string {
  return FORMATO_FECHA_LARGA.format(desdeFechaLocal(fecha));
}

export function formatearFechaCorta(fecha: string): string {
  return FORMATO_FECHA_CORTA.format(desdeFechaLocal(fecha));
}

export function nombreDiaCorto(fecha: string): string {
  const dia = desdeFechaLocal(fecha).getDay();
  const indice = dia === 0 ? 6 : dia - 1;

  return DIAS_CORTOS[indice] ?? '';
}

export function numeroDia(fecha: string): string {
  return String(desdeFechaLocal(fecha).getDate());
}

function partesDeIso(valor: string): { fecha: string; hora: string } {
  // Los turnos usan hora local sin zona. Las atenciones y los eventos pueden
  // venir con zona (UTC); en ese caso se muestran en la hora local del equipo.
  if (/(?:Z|[+-]\d{2}:?\d{2})$/.test(valor)) {
    const fecha = new Date(valor);

    if (!Number.isNaN(fecha.getTime())) {
      const anio = fecha.getFullYear();
      const mes = String(fecha.getMonth() + 1).padStart(2, '0');
      const dia = String(fecha.getDate()).padStart(2, '0');
      const hora = String(fecha.getHours()).padStart(2, '0');
      const minuto = String(fecha.getMinutes()).padStart(2, '0');

      return { fecha: `${anio}-${mes}-${dia}`, hora: `${hora}:${minuto}` };
    }
  }

  const coincidencia = /T(\d{2}):(\d{2})/.exec(valor);

  return {
    fecha: valor.slice(0, 10),
    hora: coincidencia ? `${coincidencia[1]}:${coincidencia[2]}` : '',
  };
}

/** Parte de fecha (`YYYY-MM-DD`) de un datetime ISO o local. */
export function fechaDeIso(valor: string): string {
  return partesDeIso(valor).fecha;
}

/** Parte de hora (`HH:mm`) de un datetime ISO o local. */
export function horaDeIso(valor: string): string {
  return partesDeIso(valor).hora;
}

export function formatearFechaHora(valor: string): string {
  const { fecha, hora } = partesDeIso(valor);

  return hora ? `${formatearFechaCorta(fecha)} ${hora}` : formatearFechaCorta(fecha);
}

/** datetime local sin zona horaria, como lo exige la API (`YYYY-MM-DDTHH:mm`). */
export function aDatetimeLocal(fecha: string, hora: string): string {
  return `${fecha}T${hora}`;
}
