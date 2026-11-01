import { useEffect, useRef, useState, type KeyboardEvent } from 'react';

import estilos from './Selector.module.css';

export type OpcionSelector = {
  value: string;
  label: string;
  disabled?: boolean;
};

type Props = {
  id: string;
  value: string;
  opciones: readonly OpcionSelector[];
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  required?: boolean;
  ariaLabel?: string;
};

export function Selector({
  id,
  value,
  opciones,
  onChange,
  placeholder,
  disabled = false,
  required = false,
  ariaLabel,
}: Props) {
  const [abierto, setAbierto] = useState(false);
  const [indiceActivo, setIndiceActivo] = useState(-1);
  const contenedorRef = useRef<HTMLDivElement>(null);
  const controlRef = useRef<HTMLButtonElement>(null);
  const listaId = `${id}-opciones`;
  const indiceSeleccionado = opciones.findIndex((opcion) => opcion.value === value);
  const seleccionada = opciones[indiceSeleccionado];
  const opcionesVisibles = opciones;

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

  function primerIndiceHabilitado(desde: number, direccion: 1 | -1): number {
    for (let indice = desde; indice >= 0 && indice < opcionesVisibles.length; indice += direccion) {
      if (!opcionesVisibles[indice]?.disabled) {
        return indice;
      }
    }

    return -1;
  }

  function abrir(indiceInicial = indiceSeleccionado) {
    setIndiceActivo(
      primerIndiceHabilitado(indiceInicial, 1) >= 0
        ? primerIndiceHabilitado(indiceInicial, 1)
        : primerIndiceHabilitado(0, 1),
    );
    setAbierto(true);
  }

  function elegir(opcion: OpcionSelector | undefined) {
    if (!opcion || opcion.disabled) {
      return;
    }

    onChange(opcion.value);
    setAbierto(false);
    controlRef.current?.focus();
  }

  function manejarTeclado(evento: KeyboardEvent<HTMLButtonElement>) {
    if (evento.key === 'Escape' && abierto) {
      evento.preventDefault();
      setAbierto(false);
      return;
    }

    if (evento.key === 'ArrowDown' || evento.key === 'ArrowUp') {
      evento.preventDefault();
      const direccion = evento.key === 'ArrowDown' ? 1 : -1;

      if (!abierto) {
        abrir(direccion === 1 ? indiceSeleccionado : opcionesVisibles.length - 1);
        return;
      }

      const siguiente = primerIndiceHabilitado(indiceActivo + direccion, direccion);
      if (siguiente >= 0) {
        setIndiceActivo(siguiente);
      }
      return;
    }

    if (evento.key === 'Home' || evento.key === 'End') {
      evento.preventDefault();
      const inicio = evento.key === 'Home' ? 0 : opcionesVisibles.length - 1;
      const direccion = evento.key === 'Home' ? 1 : -1;
      setIndiceActivo(primerIndiceHabilitado(inicio, direccion));
      setAbierto(true);
      return;
    }

    if (evento.key === 'Enter' || evento.key === ' ') {
      evento.preventDefault();
      if (abierto) {
        elegir(opcionesVisibles[indiceActivo]);
      } else {
        abrir();
      }
    }
  }

  return (
    <div className={estilos.contenedor} ref={contenedorRef}>
      <button
        aria-activedescendant={
          abierto && indiceActivo >= 0 ? `${listaId}-${indiceActivo}` : undefined
        }
        aria-controls={listaId}
        aria-expanded={abierto}
        aria-haspopup="listbox"
        aria-label={ariaLabel}
        aria-required={required || undefined}
        className={`${estilos.control} ${!seleccionada ? estilos.sinSeleccion : ''}`}
        disabled={disabled}
        id={id}
        onClick={() => (abierto ? setAbierto(false) : abrir())}
        onKeyDown={manejarTeclado}
        ref={controlRef}
        type="button"
        role="combobox"
      >
        <span>{seleccionada?.label ?? placeholder ?? ''}</span>
        <svg
          aria-hidden="true"
          className={`${estilos.flecha} ${abierto ? estilos.flechaAbierta : ''}`}
          fill="none"
          viewBox="0 0 20 20"
        >
          <path d="m5 7.5 5 5 5-5" />
        </svg>
      </button>

      {abierto ? (
        <div className={estilos.lista} id={listaId} role="listbox" aria-label={`${ariaLabel ?? id} opciones`}>
          {opcionesVisibles.length === 0 ? (
            <p className={estilos.sinOpciones}>No hay opciones disponibles.</p>
          ) : (
            opcionesVisibles.map((opcion, indice) => (
              <button
                aria-disabled={opcion.disabled || undefined}
                aria-selected={opcion.value === value}
                className={`${estilos.opcion} ${
                  indice === indiceActivo ? estilos.opcionActiva : ''
                }`}
                id={`${listaId}-${indice}`}
                key={`${opcion.value}-${indice}`}
                onClick={() => elegir(opcion)}
                onMouseEnter={() => setIndiceActivo(indice)}
                role="option"
                tabIndex={-1}
                type="button"
              >
                <span>{opcion.label}</span>
                {opcion.value === value ? (
                  <svg aria-hidden="true" fill="none" viewBox="0 0 20 20">
                    <path d="m4 10 4 4 8-8" />
                  </svg>
                ) : null}
              </button>
            ))
          )}
        </div>
      ) : null}
    </div>
  );
}
