import { useState } from 'react';

import type { CoincidenciaDuplicado } from '../tipos';
import estilos from '../padron.module.css';

type Props = {
  abierto: boolean;
  coincidencias: CoincidenciaDuplicado[];
  onAbrirFicha: (personaId: number) => void;
  onCrearIgual: () => void;
  onCerrar: () => void;
};

export function ModalDuplicado({
  abierto,
  coincidencias,
  onAbrirFicha,
  onCrearIgual,
  onCerrar,
}: Props) {
  const [confirmando, setConfirmando] = useState(false);

  if (!abierto) {
    return null;
  }

  function cerrar() {
    setConfirmando(false);
    onCerrar();
  }

  function abrirFicha(personaId: number) {
    setConfirmando(false);
    onAbrirFicha(personaId);
  }

  function crearIgual() {
    setConfirmando(false);
    onCrearIgual();
  }

  return (
    <div className={estilos.modalFondo}>
      <div
        aria-labelledby="titulo-modal-duplicado"
        aria-modal="true"
        className={estilos.modal}
        role="dialog"
      >
        <h2 id="titulo-modal-duplicado">¿Es esta persona?</h2>
        <p className={estilos.textoSuave}>
          Encontramos coincidencias por teléfono o por nombre parecido. Revisá antes de crear
          una persona nueva: el sistema nunca fusiona datos automáticamente.
        </p>

        <ul className={estilos.lista}>
          {coincidencias.map((coincidencia) => (
            <li className={estilos.coincidencia} key={coincidencia.persona.id}>
              <strong>
                {coincidencia.persona.apellido}, {coincidencia.persona.nombre}
              </strong>
              <span className={estilos.textoSuave}>
                {coincidencia.persona.dni
                  ? `DNI ${coincidencia.persona.dni}`
                  : 'DNI pendiente'}
              </span>
              <span className={estilos.textoSuave}>
                {coincidencia.persona.telefonos.length > 0
                  ? `Teléfono: ${coincidencia.persona.telefonos.join(' · ')}`
                  : 'Sin teléfono'}
              </span>
              <span className={estilos.textoSuave}>
                {coincidencia.mascotas.length > 0
                  ? `Mascotas: ${coincidencia.mascotas.join(', ')}`
                  : 'Sin mascotas registradas'}
              </span>
              <span className={estilos.textoSuave}>Motivo: {coincidencia.motivo}</span>

              <div>
                <button
                  className={`${estilos.boton} ${estilos.botonSecundario}`}
                  onClick={() => abrirFicha(coincidencia.persona.id)}
                  type="button"
                >
                  Es la misma persona (abrir su ficha)
                </button>
              </div>
            </li>
          ))}
        </ul>

        {confirmando ? (
          <div className={estilos.aviso} role="alert">
            <p>
              Se va a crear una persona nueva con estos datos. Confirmá que es otra persona;
              después no se pueden fusionar automáticamente.
            </p>
            <div className={estilos.pie}>
              <button className={estilos.boton} onClick={crearIgual} type="button">
                Confirmar y crear
              </button>
              <button
                className={`${estilos.boton} ${estilos.botonSecundario}`}
                onClick={() => setConfirmando(false)}
                type="button"
              >
                Volver
              </button>
            </div>
          </div>
        ) : (
          <div className={estilos.pie}>
            <button
              className={`${estilos.boton} ${estilos.botonSecundario}`}
              onClick={() => setConfirmando(true)}
              type="button"
            >
              Es otra persona, crear igual
            </button>
            <button
              className={`${estilos.boton} ${estilos.botonSecundario}`}
              onClick={cerrar}
              type="button"
            >
              Cancelar
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
