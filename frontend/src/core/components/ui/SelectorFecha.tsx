import { useEffect, useRef, useState, type ChangeEvent, type KeyboardEvent } from 'react';

import estilos from './SelectorFecha.module.css';

type Props = {
  id: string;
  etiqueta: string;
  value: string;
  onChange: (value: string) => void;
};

const DIAS_SEMANA = ['Lu', 'Ma', 'Mi', 'Ju', 'Vi', 'Sá', 'Do'];
const FORMATO_MES = new Intl.DateTimeFormat('es-AR', {
  month: 'long',
  year: 'numeric',
});

function aIso(fecha: Date): string {
  const mes = String(fecha.getMonth() + 1).padStart(2, '0');
  const dia = String(fecha.getDate()).padStart(2, '0');

  return `${fecha.getFullYear()}-${mes}-${dia}`;
}

function desdeIso(valor: string): Date | null {
  const coincidencia = /^(\d{4})-(\d{2})-(\d{2})$/.exec(valor);
  if (!coincidencia) {
    return null;
  }

  const fecha = new Date(Number(coincidencia[1]), Number(coincidencia[2]) - 1, Number(coincidencia[3]));

  return aIso(fecha) === valor ? fecha : null;
}

function desdeTexto(valor: string): Date | null {
  const iso = desdeIso(valor);
  if (iso) {
    return iso;
  }

  const coincidencia = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(valor.trim());
  if (!coincidencia) {
    return null;
  }

  const fecha = new Date(Number(coincidencia[3]), Number(coincidencia[2]) - 1, Number(coincidencia[1]));
  const dia = String(fecha.getDate()).padStart(2, '0');
  const mes = String(fecha.getMonth() + 1).padStart(2, '0');

  return dia === String(coincidencia[1]).padStart(2, '0') &&
    mes === String(coincidencia[2]).padStart(2, '0')
    ? fecha
    : null;
}

function aTexto(fecha: Date | null): string {
  if (!fecha) {
    return '';
  }

  return `${String(fecha.getDate()).padStart(2, '0')}/${String(fecha.getMonth() + 1).padStart(2, '0')}/${fecha.getFullYear()}`;
}

function nombreFecha(fecha: Date): string {
  return new Intl.DateTimeFormat('es-AR', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(fecha);
}

export function SelectorFecha({ id, etiqueta, value, onChange }: Props) {
  const [abierto, setAbierto] = useState(false);
  const [textoManual, setTextoManual] = useState<string | null>(null);
  const [mesVisible, setMesVisible] = useState(() => {
    const seleccionado = desdeIso(value) ?? new Date();
    return new Date(seleccionado.getFullYear(), seleccionado.getMonth(), 1);
  });
  const contenedorRef = useRef<HTMLDivElement>(null);
  const seleccionado = desdeIso(value);
  const texto = textoManual ?? aTexto(seleccionado);
  const diasDelMes = new Date(
    mesVisible.getFullYear(),
    mesVisible.getMonth() + 1,
    0,
  ).getDate();
  const espaciosIniciales = (new Date(
    mesVisible.getFullYear(),
    mesVisible.getMonth(),
    1,
  ).getDay() + 6) % 7;
  const hoy = aIso(new Date());

  useEffect(() => {
    if (!abierto) {
      return;
    }

    function cerrarAlHacerClicAfuera(evento: PointerEvent) {
      if (!contenedorRef.current?.contains(evento.target as Node)) {
        setAbierto(false);
      }
    }

    document.addEventListener('pointerdown', cerrarAlHacerClicAfuera);

    return () => document.removeEventListener('pointerdown', cerrarAlHacerClicAfuera);
  }, [abierto]);

  function abrirCalendario() {
    const fechaActual = desdeIso(value) ?? new Date();
    setMesVisible(new Date(fechaActual.getFullYear(), fechaActual.getMonth(), 1));
    setAbierto((actual) => !actual);
  }

  function elegirFecha(fecha: Date) {
    const fechaIso = aIso(fecha);
    onChange(fechaIso);
    setTextoManual(null);
    setAbierto(false);
  }

  function manejarTexto(evento: ChangeEvent<HTMLInputElement>) {
    const nuevoTexto = evento.target.value;
    const fechaEscrita = desdeTexto(nuevoTexto);
    setTextoManual(fechaEscrita || !nuevoTexto.trim() ? null : nuevoTexto);
    onChange(nuevoTexto.trim() && fechaEscrita ? aIso(fechaEscrita) : '');
  }

  function manejarTeclado(evento: KeyboardEvent<HTMLDivElement>) {
    if (evento.key === 'Escape' && abierto) {
      evento.preventDefault();
      setAbierto(false);
    }
  }

  return (
    <div
      className={estilos.contenedor}
      onKeyDown={manejarTeclado}
      ref={contenedorRef}
    >
      <div className={estilos.campoFecha}>
        <input
          aria-invalid={Boolean(texto.trim() && !desdeTexto(texto)) || undefined}
          autoComplete="off"
          id={id}
          inputMode="numeric"
          onBlur={() => {
            if (texto.trim() && !desdeTexto(texto)) {
              setTextoManual(null);
            }
          }}
          onChange={manejarTexto}
          placeholder="dd/mm/aaaa"
          type="text"
          value={texto}
        />
        <button
          aria-expanded={abierto}
          aria-haspopup="dialog"
          aria-label={`Abrir calendario: ${etiqueta}`}
          className={estilos.botonCalendario}
          onClick={abrirCalendario}
          type="button"
        >
          <svg aria-hidden="true" fill="none" viewBox="0 0 24 24">
            <rect height="16" rx="2.5" width="18" x="3" y="5" />
            <path d="M16 3v4M8 3v4M3 10h18" />
            <path d="M8 14h.01M12 14h.01M16 14h.01M8 18h.01M12 18h.01" />
          </svg>
        </button>
      </div>

      {abierto ? (
        <section
          aria-label={`Calendario: ${etiqueta}`}
          className={estilos.calendario}
          role="dialog"
        >
          <header className={estilos.encabezado}>
            <button
              aria-label="Mes anterior"
              className={estilos.navegacion}
              onClick={() =>
                setMesVisible(
                  (mes) => new Date(mes.getFullYear(), mes.getMonth() - 1, 1),
                )
              }
              type="button"
            >
              <svg aria-hidden="true" fill="none" viewBox="0 0 20 20">
                <path d="m12.5 4-6 6 6 6" />
              </svg>
            </button>
            <h2>{FORMATO_MES.format(mesVisible)}</h2>
            <button
              aria-label="Mes siguiente"
              className={estilos.navegacion}
              onClick={() =>
                setMesVisible(
                  (mes) => new Date(mes.getFullYear(), mes.getMonth() + 1, 1),
                )
              }
              type="button"
            >
              <svg aria-hidden="true" fill="none" viewBox="0 0 20 20">
                <path d="m7.5 4 6 6-6 6" />
              </svg>
            </button>
          </header>

          <table className={estilos.tabla}>
            <thead>
              <tr>
                {DIAS_SEMANA.map((dia) => (
                  <th key={dia} scope="col">
                    {dia}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {Array.from({ length: Math.ceil((espaciosIniciales + diasDelMes) / 7) }, (_, semana) => (
                <tr key={semana}>
                  {Array.from({ length: 7 }, (_, columna) => {
                    const numeroDia = semana * 7 + columna - espaciosIniciales + 1;
                    if (numeroDia < 1 || numeroDia > diasDelMes) {
                      return <td aria-hidden="true" key={columna} />;
                    }

                    const fecha = new Date(
                      mesVisible.getFullYear(),
                      mesVisible.getMonth(),
                      numeroDia,
                    );
                    const fechaIso = aIso(fecha);

                    return (
                      <td key={columna}>
                        <button
                          aria-label={nombreFecha(fecha)}
                          aria-pressed={fechaIso === value}
                          className={`${estilos.dia} ${
                            fechaIso === hoy ? estilos.hoy : ''
                          } ${fechaIso === value ? estilos.diaSeleccionado : ''}`}
                          onClick={() => elegirFecha(fecha)}
                          type="button"
                        >
                          {numeroDia}
                        </button>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ) : null}
    </div>
  );
}
