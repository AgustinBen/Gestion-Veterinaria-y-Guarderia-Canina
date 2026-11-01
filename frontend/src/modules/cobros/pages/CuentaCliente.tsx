import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { BannerDeuda } from '../../../core/components/BannerDeuda';
import { Alerta } from '../../../core/components/ui/Alerta';
import { Boton } from '../../../core/components/ui/Boton';
import { DialogoConfirmacion } from '../../../core/components/ui/DialogoConfirmacion';
import { formatearDinero } from '../../../core/formatos/dinero';
import {
  listarMediosPago,
  mensajeDeError,
  obtenerCuentaCliente,
  obtenerPersona,
  obtenerResumenDeuda,
} from '../api';
import { DialogoAjuste } from '../components/DialogoAjuste';
import { FormularioPago } from '../components/FormularioPago';
import { TablaCargos } from '../components/TablaCargos';
import type {
  CargoDetalle,
  CuentaCliente as CuentaClienteDatos,
  MedioPago,
  Pago,
  PersonaBusqueda,
  ResumenDeuda,
} from '../tipos';
import estilos from '../cobros.module.css';

type Estado = 'cargando' | 'listo' | 'error';
const TAMANIO_PAGINA_CARGOS = 20;

type DatosPagina = {
  estado: Estado;
  persona: PersonaBusqueda | null;
  cuenta: CuentaClienteDatos | null;
  resumen: ResumenDeuda | null;
  medios: MedioPago[];
  error: string;
};

type Carga = DatosPagina & { intento: number; personaId: number | null };

const CARGA_INICIAL: Carga = {
  intento: 0,
  personaId: null,
  estado: 'cargando',
  persona: null,
  cuenta: null,
  resumen: null,
  medios: [],
  error: '',
};

function numeroPositivo(valor: string | undefined): number | null {
  if (!valor) {
    return null;
  }

  const numero = Number(valor);

  return Number.isSafeInteger(numero) && numero > 0 ? numero : null;
}

function pagosPorCargo(cuenta: CuentaClienteDatos): Record<number, Pago[]> {
  const mapa: Record<number, Pago[]> = {};

  for (const item of cuenta.cargos) {
    mapa[item.cargo.id] = item.pagos;
  }

  return mapa;
}

/** Cuenta corriente del cliente: saldo, cargos, pagos y ajustes. */
export function CuentaCliente() {
  const { personaId } = useParams();
  const id = numeroPositivo(personaId);
  const [paginaCargos, setPaginaCargos] = useState<{
    personaId: number | null;
    indice: number;
  }>({ personaId: null, indice: 0 });
  const [intento, setIntento] = useState(0);
  const [carga, setCarga] = useState<Carga>(CARGA_INICIAL);
  const [cargoPago, setCargoPago] = useState<CargoDetalle | null>(null);
  const [cargoAjuste, setCargoAjuste] = useState<CargoDetalle | null>(null);
  const [registrandoPago, setRegistrandoPago] = useState(false);
  const [aviso, setAviso] = useState('');

  useEffect(() => {
    if (id === null) {
      return;
    }

    const control = new AbortController();
    let activo = true;

    Promise.all([
      obtenerPersona(id, { signal: control.signal }),
      obtenerCuentaCliente(id, { signal: control.signal }),
      obtenerResumenDeuda(id, { signal: control.signal }),
      // Si fallan los medios, la cuenta igual se muestra: solo se pierden los
      // nombres de los medios en el detalle de los pagos.
      listarMediosPago({ signal: control.signal }).catch(() => [] as MedioPago[]),
    ])
      .then(([persona, cuenta, resumen, medios]) => {
        if (!activo || control.signal.aborted) {
          return;
        }

        setCarga({
          intento,
          personaId: id,
          estado: 'listo',
          persona,
          cuenta,
          resumen,
          medios,
          error: '',
        });
      })
      .catch((fallo) => {
        if (!activo || control.signal.aborted) {
          return;
        }

        setCarga({
          intento,
          personaId: id,
          estado: 'error',
          persona: null,
          cuenta: null,
          resumen: null,
          medios: [],
          error: mensajeDeError(fallo),
        });
      });

    return () => {
      activo = false;
      control.abort();
    };
  }, [id, intento]);

  const mediosPorId = useMemo(() => {
    const mapa: Record<number, string> = {};

    for (const medio of carga.medios) {
      mapa[medio.id] = medio.nombre;
    }

    return mapa;
  }, [carga.medios]);

  if (id === null) {
    return (
      <section className={estilos.pagina}>
        <Alerta role="alert" tono="error">
          El cliente indicado no es válido.
        </Alerta>
        <Link className={estilos.enlace} to="/cobros">
          Volver a Cobros
        </Link>
      </section>
    );
  }

  const vigente =
    carga.intento === intento && carga.personaId === id ? carga : null;
  const estado: Estado = vigente?.estado ?? 'cargando';
  const persona = vigente?.persona ?? null;
  const cuenta = vigente?.cuenta ?? null;
  const resumen = vigente?.resumen ?? null;

  function recargar(mensaje: string) {
    setAviso(mensaje);
    setIntento((valor) => valor + 1);
  }

  if (estado === 'cargando') {
    return (
      <section className={estilos.pagina}>
        <p className={estilos.cargando} role="status">
          Cargando cuenta…
        </p>
      </section>
    );
  }

  if (estado === 'error' || !persona || !cuenta || !resumen) {
    return (
      <section className={estilos.pagina}>
        <div className={estilos.cabecera}>
          <h1 className={estilos.titulo}>Cuenta del cliente</h1>
        </div>
        <Alerta
          acciones={
            <Boton
              onClick={() => setIntento((valor) => valor + 1)}
              variante="secundario"
            >
              Reintentar
            </Boton>
          }
          role="alert"
          tono="error"
        >
          {carga.error || 'No pudimos cargar la cuenta del cliente.'}
        </Alerta>
        <Link className={estilos.enlace} to="/cobros">
          Volver a Cobros
        </Link>
      </section>
    );
  }

  const pagos = pagosPorCargo(cuenta);
  const cargos = cuenta.cargos.map((item) => item.cargo);
  const totalCargosCentavos = cargos.reduce(
    (total, cargo) => total + cargo.total_vigente,
    0,
  );
  const totalPagadoCentavos = cargos.reduce(
    (total, cargo) => total + cargo.total_pagado,
    0,
  );
  const indicePagina = paginaCargos.personaId === id ? paginaCargos.indice : 0;
  const cargosVisibles = cargos.slice(
    indicePagina * TAMANIO_PAGINA_CARGOS,
    (indicePagina + 1) * TAMANIO_PAGINA_CARGOS,
  );
  const paginasCargos = Math.ceil(cargos.length / TAMANIO_PAGINA_CARGOS);

  return (
    <section className={estilos.pagina} aria-labelledby="titulo-cuenta">
      <header className={estilos.encabezadoCuenta}>
        <div className={estilos.identidadCliente}>
          <span className={estilos.avatarCuenta} aria-hidden="true">
            {persona.nombre.charAt(0)}
            {persona.apellido.charAt(0)}
          </span>
          <div className={estilos.datosCliente}>
            <p className={estilos.antetitulo}>Cuenta del cliente</p>
            <h1 className={estilos.titulo} id="titulo-cuenta">
              {persona.apellido}, {persona.nombre}
            </h1>
            <div className={estilos.contactoCliente}>
              {persona.dni ? (
                <span>DNI {persona.dni}</span>
              ) : (
                <span>Sin DNI registrado</span>
              )}
              {persona.telefonos.map((telefono) => (
                <span key={telefono}>{telefono}</span>
              ))}
            </div>
          </div>
        </div>
        <div className={estilos.acciones}>
          <Link className={estilos.botonEnlaceSecundario} to="/cobros">
            <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M19 12H5m7 7-7-7 7-7" />
            </svg>
            Volver a Cobros
          </Link>
        </div>
      </header>

      <BannerDeuda
        debe={resumen.debe}
        deudaMasAntigua={resumen.deuda_mas_antigua}
        saldoTotalCentavos={resumen.saldo_total_centavos}
      />

      <section className={estilos.resumenCuenta} aria-label="Resumen de la cuenta">
        <article className={`${estilos.indicadorCuenta} ${estilos.indicadorSaldo}`}>
          <span className={estilos.indicadorIcono} aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none">
              <path d="M4 7.5h15a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6.5a2 2 0 0 1 2-2h13" />
              <path d="M16 13.5h5m-15-6h13" />
              <circle cx="16" cy="13.5" r=".75" />
            </svg>
          </span>
          <span className={estilos.indicadorEtiqueta}>Saldo pendiente</span>
          <strong className={estilos.indicadorMonto}>
            {formatearDinero(resumen.saldo_total_centavos)}
          </strong>
          <span className={estilos.indicadorDetalle}>
            {resumen.debe ? 'Saldo por cobrar' : 'Cuenta al día'}
          </span>
        </article>
        <article className={estilos.indicadorCuenta}>
          <span
            className={`${estilos.indicadorIcono} ${estilos.iconoCargos}`}
            aria-hidden="true"
          >
            <svg viewBox="0 0 24 24" fill="none">
              <path d="M7 3.75h7l4 4v12.5H7a2 2 0 0 1-2-2V5.75a2 2 0 0 1 2-2Z" />
              <path d="M14 3.75v4h4m-9 4h6m-6 4h6" />
            </svg>
          </span>
          <span className={estilos.indicadorEtiqueta}>Cargos registrados</span>
          <strong className={estilos.indicadorNumero}>{cargos.length}</strong>
          <span className={estilos.indicadorDetalle}>En esta cuenta</span>
        </article>
        <article className={estilos.indicadorCuenta}>
          <span
            className={`${estilos.indicadorIcono} ${estilos.iconoPagos}`}
            aria-hidden="true"
          >
            <svg viewBox="0 0 24 24" fill="none">
              <path d="M5 12.5 9.5 17 19 7.5" />
              <circle cx="12" cy="12" r="9" />
            </svg>
          </span>
          <span className={estilos.indicadorEtiqueta}>Total abonado</span>
          <strong className={estilos.indicadorMonto}>
            {formatearDinero(totalPagadoCentavos)}
          </strong>
          <span className={estilos.indicadorDetalle}>
            Sobre {formatearDinero(totalCargosCentavos)} en cargos
          </span>
        </article>
      </section>

      {aviso ? (
        <Alerta role="status" tono="exito">
          {aviso}
        </Alerta>
      ) : null}

      <section className={estilos.historialCuenta} aria-labelledby="titulo-cargos">
        <div className={estilos.encabezadoHistorial}>
          <div>
            <h2 className={estilos.tituloSeccion} id="titulo-cargos">
              Cargos y pagos
            </h2>
          </div>
          {cargos.length > 0 ? (
            <span className={estilos.cantidadCargos}>
              {cargos.length} {cargos.length === 1 ? 'cargo' : 'cargos'}
            </span>
          ) : null}
        </div>
        {cargos.length === 0 ? (
          <p className={estilos.vacio}>Este cliente todavía no tiene cargos.</p>
        ) : (
          <TablaCargos
            cargos={cargosVisibles}
            mediosPorId={mediosPorId}
            onAjustar={setCargoAjuste}
            onCobrar={setCargoPago}
            pagosPorCargo={pagos}
          />
        )}
        {paginasCargos > 1 ? (
          <nav className={estilos.paginacion} aria-label="Paginación de cargos">
            <button
              className={estilos.botonPaginacion}
              disabled={indicePagina === 0}
              onClick={() =>
                setPaginaCargos({ personaId: id, indice: Math.max(0, indicePagina - 1) })
              }
              type="button"
            >
              Anterior
            </button>
            <span className={estilos.estadoPaginacion}>
              Página {indicePagina + 1} de {paginasCargos}
            </span>
            <button
              className={estilos.botonPaginacion}
              disabled={indicePagina + 1 >= paginasCargos}
              onClick={() =>
                setPaginaCargos({ personaId: id, indice: indicePagina + 1 })
              }
              type="button"
            >
              Siguiente
            </button>
          </nav>
        ) : null}
      </section>

      {cargoPago ? (
        <DialogoConfirmacion
          abierto
          bloquearCierre={registrandoPago}
          onCerrar={() => setCargoPago(null)}
          titulo={`Cobrar: ${cargoPago.concepto}`}
        >
          <FormularioPago
            cargo={cargoPago}
            onEnviandoChange={setRegistrandoPago}
            onCancelar={() => setCargoPago(null)}
            onPagado={() => {
              setCargoPago(null);
              recargar('Pago registrado.');
            }}
          />
        </DialogoConfirmacion>
      ) : null}

      {cargoAjuste ? (
        <DialogoAjuste
          abierto
          cargo={cargoAjuste}
          onAjustado={() => {
            setCargoAjuste(null);
            recargar('Precio actualizado.');
          }}
          onCerrar={() => setCargoAjuste(null)}
        />
      ) : null}
    </section>
  );
}
