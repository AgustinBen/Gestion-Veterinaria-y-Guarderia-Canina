import { Fragment } from 'react';

import { Boton } from '../../../core/components/ui/Boton';
import { formatearDinero } from '../../../core/formatos/dinero';

import type { CargoDetalle, Pago } from '../tipos';
import estilos from '../cobros.module.css';

type Props = {
  cargos: CargoDetalle[];
  pagosPorCargo?: Record<number, Pago[]>;
  mediosPorId?: Record<number, string>;
  onCobrar: (cargo: CargoDetalle) => void;
  onAjustar?: (cargo: CargoDetalle) => void;
};

/** "2026-03-05" → "05/03/2026" sin pasar por zonas horarias. */
function formatearFecha(fecha: string): string {
  const coincidencia = /^(\d{4})-(\d{2})-(\d{2})/.exec(fecha);

  return coincidencia
    ? `${coincidencia[3]}/${coincidencia[2]}/${coincidencia[1]}`
    : fecha;
}

export function TablaCargos({
  cargos,
  pagosPorCargo = {},
  mediosPorId = {},
  onCobrar,
  onAjustar,
}: Props) {
  return (
    <div className={estilos.tablaMarco}>
      <table className={estilos.tabla}>
        <caption className="sr-only">Cargos del cliente</caption>
        <thead>
          <tr>
            <th scope="col">Concepto</th>
            <th scope="col" className={estilos.numero}>
              Total
            </th>
            <th scope="col" className={estilos.numero}>
              Pagado
            </th>
            <th scope="col" className={estilos.numero}>
              Saldo
            </th>
            <th scope="col" className={estilos.numero}>
              Acciones
            </th>
          </tr>
        </thead>
        <tbody>
          {cargos.map((cargo) => {
            const pagos = pagosPorCargo[cargo.id] ?? [];
            const pendiente = cargo.saldo > 0;

            return (
              <Fragment key={cargo.id}>
                <tr>
                  <td data-etiqueta="Concepto">
                    <span className={estilos.concepto}>
                      <strong>{cargo.concepto}</strong>
                      {cargo.origen === 'MIGRACION' ? (
                        <span className={`${estilos.insignia} ${estilos.insigniaAviso}`}>
                          Migrado
                        </span>
                      ) : null}
                    </span>
                  </td>
                  <td className={estilos.numero} data-etiqueta="Total">
                    {formatearDinero(cargo.total_vigente)}
                  </td>
                  <td className={estilos.numero} data-etiqueta="Pagado">
                    {formatearDinero(cargo.total_pagado)}
                  </td>
                  <td className={estilos.numero} data-etiqueta="Saldo">
                    <strong>{formatearDinero(cargo.saldo)}</strong>
                  </td>
                  <td className={estilos.numero} data-etiqueta="Acciones">
                    <div className={estilos.accionesFila}>
                      {pendiente ? (
                        <>
                          <Boton onClick={() => onCobrar(cargo)}>Cobrar</Boton>
                          {onAjustar ? (
                            <Boton
                              onClick={() => onAjustar(cargo)}
                              variante="secundario"
                            >
                              Ajustar precio
                            </Boton>
                          ) : null}
                        </>
                      ) : (
                        <span className={`${estilos.insignia} ${estilos.insigniaExito}`}>
                          Saldado
                        </span>
                      )}
                    </div>
                  </td>
                </tr>

                {pagos.length > 0 ? (
                  <tr className={estilos.filaPagos}>
                    <td colSpan={5} data-etiqueta="Pagos">
                      <ul className={estilos.pagos}>
                        {pagos.map((pago) => {
                          const medio = mediosPorId[pago.medio_pago_id];

                          return (
                            <li className={estilos.pago} key={pago.id}>
                              <span className={estilos.pagoMonto}>
                                {formatearDinero(pago.monto)}
                              </span>
                              <span>{formatearFecha(pago.fecha)}</span>
                              {medio ? <span>{medio}</span> : null}
                              {pago.es_sena ? (
                                <span className={estilos.insignia}>Seña</span>
                              ) : null}
                              {pago.tipo === 'REVERSO' ? (
                                <span className={estilos.insigniaAviso}>Reverso</span>
                              ) : null}
                            </li>
                          );
                        })}
                      </ul>
                    </td>
                  </tr>
                ) : null}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
