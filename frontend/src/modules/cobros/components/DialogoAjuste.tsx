import { useState } from 'react';

import { Alerta } from '../../../core/components/ui/Alerta';
import { Boton } from '../../../core/components/ui/Boton';
import { Campo } from '../../../core/components/ui/Campo';
import { DialogoConfirmacion } from '../../../core/components/ui/DialogoConfirmacion';
import { formatearDinero, formatearMonto, parsearDinero } from '../../../core/formatos/dinero';
import { ajustarPrecio, mensajeDeError } from '../api';
import { usePuedeBajarPrecio } from '../permisos';
import type { AjustePrecio, CargoDetalle } from '../tipos';
import estilos from '../cobros.module.css';

type Props = {
  abierto: boolean;
  cargo: CargoDetalle;
  onCerrar: () => void;
  onAjustado: (ajuste: AjustePrecio) => void;
};

type Etapa = 'editar' | 'confirmar';

const ID_NUEVO_TOTAL = 'ajuste-total';
const ID_MOTIVO = 'ajuste-motivo';

/**
 * Ajuste de precio de un cargo (RN-22).
 *
 * El precio nuevo no puede quedar por debajo de lo ya pagado. Bajarlo solo lo
 * puede hacer el Dueño; subirlo, cualquier rol con permiso de cobro. La UI
 * muestra y frena lo que puede, pero el backend sigue siendo la autoridad.
 */
export function DialogoAjuste({ abierto, cargo, onCerrar, onAjustado }: Props) {
  const puedeBajar = usePuedeBajarPrecio();
  const [etapa, setEtapa] = useState<Etapa>('editar');
  const [montoTexto, setMontoTexto] = useState(() =>
    formatearMonto(cargo.total_vigente),
  );
  const [motivo, setMotivo] = useState('');
  const [errorEnvio, setErrorEnvio] = useState('');
  const [enviando, setEnviando] = useState(false);

  let nuevoTotal: number | null = null;
  let mensajeMonto = '';

  try {
    nuevoTotal = parsearDinero(montoTexto);
  } catch (fallo) {
    mensajeMonto = fallo instanceof Error ? fallo.message : 'Monto inválido.';
  }

  const igualAlActual = nuevoTotal !== null && nuevoTotal === cargo.total_vigente;
  const menorALoPagado = nuevoTotal !== null && nuevoTotal < cargo.total_pagado;
  const esBaja = nuevoTotal !== null && nuevoTotal < cargo.total_vigente;
  const bajaBloqueada = esBaja && !puedeBajar;
  const motivoCompleto = motivo.trim().length > 0;

  const puedeContinuar =
    nuevoTotal !== null &&
    !igualAlActual &&
    !menorALoPagado &&
    !bajaBloqueada &&
    motivoCompleto;

  function continuar() {
    if (!puedeContinuar) {
      return;
    }

    setErrorEnvio('');
    setEtapa('confirmar');
  }

  async function confirmar() {
    if (nuevoTotal === null || !puedeContinuar || enviando) {
      return;
    }

    setEnviando(true);
    setErrorEnvio('');

    try {
      const ajuste = await ajustarPrecio(cargo.id, {
        nuevo_total_centavos: nuevoTotal,
        motivo: motivo.trim(),
      });

      onAjustado(ajuste);
    } catch (fallo) {
      setErrorEnvio(mensajeDeError(fallo));
    } finally {
      setEnviando(false);
    }
  }

  const pie =
    etapa === 'editar' ? (
      <>
        <Boton onClick={onCerrar} variante="secundario">
          Cancelar
        </Boton>
        <Boton disabled={!puedeContinuar} onClick={continuar}>
          Continuar
        </Boton>
      </>
    ) : (
      <>
        <Boton
          disabled={enviando}
          onClick={() => setEtapa('editar')}
          variante="secundario"
        >
          Volver
        </Boton>
        <Boton cargando={enviando} onClick={confirmar}>
          Confirmar ajuste
        </Boton>
      </>
    );

  return (
    <DialogoConfirmacion
      abierto={abierto}
      descripcion={`Cargo: ${cargo.concepto}`}
      onCerrar={onCerrar}
      pie={pie}
      titulo="Ajustar precio"
    >
      {etapa === 'editar' ? (
        <>
          <div className={estilos.resumenAjuste}>
            <span className={estilos.resumenLinea}>
              <span>Precio actual</span>
              <strong>{formatearDinero(cargo.total_vigente)}</strong>
            </span>
            <span className={estilos.resumenLinea}>
              <span>Pagado</span>
              <strong>{formatearDinero(cargo.total_pagado)}</strong>
            </span>
          </div>

          <Campo
            ayuda="El precio puede subir o bajar, pero nunca quedar por debajo de lo pagado."
            error={mensajeMonto}
            etiqueta="Precio nuevo"
            id={ID_NUEVO_TOTAL}
          >
            <input
              autoComplete="off"
              id={ID_NUEVO_TOTAL}
              inputMode="decimal"
              onChange={(evento) => setMontoTexto(evento.target.value)}
              value={montoTexto}
            />
          </Campo>

          <Campo etiqueta="Motivo" id={ID_MOTIVO}>
            <textarea
              id={ID_MOTIVO}
              onChange={(evento) => setMotivo(evento.target.value)}
              placeholder="Ej.: descuento a cliente frecuente"
              rows={3}
              value={motivo}
            />
          </Campo>

          {igualAlActual ? (
            <Alerta tono="aviso">
              El precio nuevo debe ser distinto del actual.
            </Alerta>
          ) : null}

          {menorALoPagado ? (
            <Alerta tono="error">
              El precio nuevo no puede ser menor a lo ya pagado (
              {formatearDinero(cargo.total_pagado)}).
            </Alerta>
          ) : null}

          {bajaBloqueada ? (
            <Alerta tono="error">
              Bajar el precio solo lo puede hacer el Dueño. Podés subirlo o
              pedirle a un Dueño que lo ajuste.
            </Alerta>
          ) : null}

          {errorEnvio ? (
            <Alerta role="alert" tono="error">
              {errorEnvio}
            </Alerta>
          ) : null}
        </>
      ) : (
        <>
          <div className={estilos.resumenAjuste}>
            <span className={estilos.resumenLinea}>
              <span>Precio actual</span>
              <strong>{formatearDinero(cargo.total_vigente)}</strong>
            </span>
            <span className={estilos.resumenLinea}>
              <span>Precio nuevo</span>
              <strong>{nuevoTotal === null ? '—' : formatearDinero(nuevoTotal)}</strong>
            </span>
            <span className={estilos.resumenLinea}>
              <span>Pagado</span>
              <strong>{formatearDinero(cargo.total_pagado)}</strong>
            </span>
            <span className={estilos.resumenLinea}>
              <span>Motivo</span>
              <strong>{motivo.trim()}</strong>
            </span>
          </div>

          <p className={estilos.textoSuave}>
            Confirmá el nuevo precio. Queda registrado quién lo cambió, el precio
            anterior, el nuevo y el motivo.
          </p>

          {errorEnvio ? (
            <Alerta role="alert" tono="error">
              {errorEnvio}
            </Alerta>
          ) : null}
        </>
      )}
    </DialogoConfirmacion>
  );
}
