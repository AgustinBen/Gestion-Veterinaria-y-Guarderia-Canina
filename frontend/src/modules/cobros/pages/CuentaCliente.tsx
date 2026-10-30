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

  return (
    <section className={estilos.pagina} aria-labelledby="titulo-cuenta">
      <div className={estilos.cabecera}>
        <div>
          <h1 className={estilos.titulo} id="titulo-cuenta">
            {persona.apellido}, {persona.nombre}
          </h1>
          <p className={estilos.subtitulo}>
            {persona.dni ? `DNI ${persona.dni}` : 'Sin DNI registrado'}
            {persona.telefonos.length > 0
              ? ` · Tel. ${persona.telefonos.join(' · ')}`
              : ''}
          </p>
        </div>

        <div className={estilos.acciones}>
          <Link className={estilos.botonEnlaceSecundario} to="/cobros">
            Volver a Cobros
          </Link>
        </div>
      </div>

      <BannerDeuda
        debe={resumen.debe}
        deudaMasAntigua={resumen.deuda_mas_antigua}
        personaId={persona.id}
        saldoTotalCentavos={resumen.saldo_total_centavos}
      />

      <div className={estilos.saldoCaja}>
        <span className={estilos.saldoEtiqueta}>Saldo total</span>
        <span
          className={[
            estilos.saldoMonto,
            cuenta.saldo_total > 0 ? estilos.saldoMontoConDeuda : '',
          ]
            .filter(Boolean)
            .join(' ')}
        >
          {formatearDinero(cuenta.saldo_total)}
        </span>
        <span className={estilos.textoSuave}>
          {cuenta.saldo_total > 0
            ? `Deuda calculada automáticamente. Cargos pendientes: ${resumen.cargos_pendientes}.`
            : 'Sin deuda pendiente.'}
        </span>
      </div>

      {aviso ? (
        <Alerta role="status" tono="exito">
          {aviso}
        </Alerta>
      ) : null}

      <div className={estilos.cabecera}>
        <div>
          <h2 className={estilos.tituloSeccion}>Cargos y pagos</h2>
          <p className={estilos.subtitulo}>
            Cada cargo muestra su total, lo pagado y el saldo.
          </p>
        </div>
      </div>

      {cargos.length === 0 ? (
        <p className={estilos.vacio}>Este cliente todavía no tiene cargos.</p>
      ) : (
        <TablaCargos
          cargos={cargos}
          mediosPorId={mediosPorId}
          onAjustar={setCargoAjuste}
          onCobrar={setCargoPago}
          pagosPorCargo={pagos}
        />
      )}

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
