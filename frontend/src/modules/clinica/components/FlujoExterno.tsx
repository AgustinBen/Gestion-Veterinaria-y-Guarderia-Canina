import { useEffect, useState, type FormEvent } from 'react';

import { Alerta } from '../../../core/components/ui/Alerta';
import { Boton } from '../../../core/components/ui/Boton';
import { Campo } from '../../../core/components/ui/Campo';
import { formatearDinero, parsearDinero } from '../../../core/formatos/dinero';
import type { EmpleadoDetalle } from '../../padron/tipos';
import {
  confirmarExterno,
  contactarExterno,
  listarEventosExterno,
  mensajeDeError,
  rechazarExterno,
  reemplazarExterno,
} from '../api';
import { formatearFechaHora } from '../fechas';
import type {
  EventoExterno,
  MedioEventoExterno,
  TipoEventoExterno,
} from '../tipos';
import estilos from '../clinica.module.css';

const MEDIOS: { value: MedioEventoExterno; label: string }[] = [
  { value: 'TELEFONO', label: 'Teléfono' },
  { value: 'WHATSAPP', label: 'WhatsApp' },
  { value: 'PRESENCIAL', label: 'Presencial' },
  { value: 'OTRO', label: 'Otro' },
];

const ETIQUETA_MEDIO = Object.fromEntries(
  MEDIOS.map((medio) => [medio.value, medio.label]),
) as Record<MedioEventoExterno, string>;

const ETIQUETA_EVENTO: Record<TipoEventoExterno, string> = {
  CONTACTADO: 'Contactado',
  CONFIRMADO: 'Confirmado',
  RECHAZADO: 'Rechazado',
  REEMPLAZADO: 'Reemplazado',
};

type Accion = 'contacto' | 'confirmar' | 'rechazar' | 'reemplazar';

const TITULO_ACCION: Record<Accion, string> = {
  contacto: 'Registrar contacto',
  confirmar: 'Confirmar costo acordado',
  rechazar: 'Rechazar veterinario externo',
  reemplazar: 'Reemplazar veterinario externo',
};

type Props = {
  turnoId: number;
  empleados: EmpleadoDetalle[];
  puedeConfirmarCosto: boolean;
  onEvento?: (evento: EventoExterno) => void;
};

export function FlujoExterno({
  turnoId,
  empleados,
  puedeConfirmarCosto,
  onEvento,
}: Props) {
  const externos = empleados.filter(
    (empleado) => empleado.tipo === 'EXTERNO' && empleado.activo,
  );
  const [eventos, setEventos] = useState<EventoExterno[]>([]);
  const [estado, setEstado] = useState<'cargando' | 'listo' | 'error'>(
    'cargando',
  );
  const [errorCarga, setErrorCarga] = useState('');
  const [intento, setIntento] = useState(0);
  const [accion, setAccion] = useState<Accion | null>(null);
  const [medio, setMedio] = useState<MedioEventoExterno>('TELEFONO');
  const [nota, setNota] = useState('');
  const [motivo, setMotivo] = useState('');
  const [costo, setCosto] = useState('');
  const [externoId, setExternoId] = useState(
    String(externos[0]?.persona_id ?? ''),
  );
  const [error, setError] = useState('');
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    const controlador = new AbortController();
    let activo = true;

    async function cargar() {
      setEstado('cargando');
      setErrorCarga('');

      try {
        const datos = await listarEventosExterno(turnoId, {
          signal: controlador.signal,
        });

        if (activo) {
          setEventos(datos);
          setEstado('listo');
        }
      } catch (fallo) {
        if (!activo || controlador.signal.aborted) {
          return;
        }

        setErrorCarga(mensajeDeError(fallo));
        setEstado('error');
      }
    }

    void cargar();

    return () => {
      activo = false;
      controlador.abort();
    };
  }, [turnoId, intento]);

  function cerrar() {
    setAccion(null);
    setError('');
    setNota('');
    setMotivo('');
    setCosto('');
  }

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();

    if (!accion) {
      return;
    }

    setError('');
    setGuardando(true);

    try {
      let registrado: EventoExterno;

      if (accion === 'contacto') {
        registrado = await contactarExterno(turnoId, {
          medio,
          nota: nota.trim() || null,
        });
      } else if (accion === 'confirmar') {
        if (!puedeConfirmarCosto) {
          setError('Solo el Dueño puede acordar el costo de un externo.');
          return;
        }

        let centavos: number;

        try {
          centavos = parsearDinero(costo);
        } catch (fallo) {
          setError(mensajeDeError(fallo));
          return;
        }

        registrado = await confirmarExterno(turnoId, centavos);
      } else if (accion === 'rechazar') {
        if (motivo.trim().length === 0) {
          setError('Indicá el motivo del rechazo.');
          return;
        }

        registrado = await rechazarExterno(turnoId, motivo.trim());
      } else {
        if (externoId === '') {
          setError('Elegí el veterinario externo de reemplazo.');
          return;
        }

        registrado = await reemplazarExterno(turnoId, Number(externoId));
      }

      setEventos((actuales) => [...actuales, registrado]);
      onEvento?.(registrado);
      cerrar();
    } catch (fallo) {
      setError(mensajeDeError(fallo));
    } finally {
      setGuardando(false);
    }
  }

  return (
    <section className={estilos.panel} aria-labelledby="externo-titulo">
      <div className={estilos.panelCabecera}>
        <h2 className={estilos.panelTitulo} id="externo-titulo">
          Veterinario externo
        </h2>
        <span className={estilos.etiqueta}>{eventos.length} eventos</span>
      </div>

      {estado === 'cargando' ? (
        <p className={estilos.cargando}>Cargando eventos…</p>
      ) : estado === 'error' ? (
        <Alerta
          acciones={
            <Boton
              onClick={() => setIntento((actual) => actual + 1)}
              variante="secundario"
            >
              Reintentar
            </Boton>
          }
          role="alert"
          tono="error"
        >
          {errorCarga}
        </Alerta>
      ) : eventos.length === 0 ? (
        <p className={estilos.vacio}>Sin eventos registrados.</p>
      ) : (
        <ul className={estilos.lista}>
          {eventos.map((evento) => (
            <li className={estilos.tarjeta} key={evento.id}>
              <div className={estilos.tarjetaCabecera}>
                <strong className={estilos.tarjetaTitulo}>
                  {ETIQUETA_EVENTO[evento.tipo]}
                </strong>
                <span className={estilos.etiqueta}>
                  {formatearFechaHora(evento.created_at)}
                </span>
              </div>
              <div className={estilos.meta}>
                <span>
                  Externo:{' '}
                  <strong>
                    {evento.externo_nombre ?? `#${evento.externo_empleado_id}`}
                  </strong>
                </span>
                {evento.medio ? (
                  <span>Medio: {ETIQUETA_MEDIO[evento.medio]}</span>
                ) : null}
                {evento.costo_acordado_centavos !== null &&
                puedeConfirmarCosto ? (
                  <span>
                    Costo acordado:{' '}
                    <strong>
                      {formatearDinero(evento.costo_acordado_centavos)}
                    </strong>
                  </span>
                ) : evento.costo_registrado ? (
                  <span>Costo registrado (visible para el Dueño)</span>
                ) : null}
              </div>
              {evento.nota ? <p>{evento.nota}</p> : null}
            </li>
          ))}
        </ul>
      )}

      {estado === 'listo' ? (
        <div className={estilos.acciones}>
          <Boton
            onClick={() => setAccion('contacto')}
            type="button"
            variante="secundario"
          >
            Registrar contacto
          </Boton>
          {puedeConfirmarCosto ? (
            <Boton onClick={() => setAccion('confirmar')} type="button">
              Confirmar costo
            </Boton>
          ) : null}
          <Boton
            onClick={() => setAccion('rechazar')}
            type="button"
            variante="secundario"
          >
            Rechazar
          </Boton>
          <Boton
            onClick={() => setAccion('reemplazar')}
            type="button"
            variante="secundario"
          >
            Reemplazar
          </Boton>
        </div>
      ) : null}

      {accion ? (
        <form className={estilos.formulario} onSubmit={(evento) => void enviar(evento)}>
          <h3 className={estilos.panelTitulo}>{TITULO_ACCION[accion]}</h3>

          {error ? (
            <Alerta role="alert" tono="error">
              {error}
            </Alerta>
          ) : null}

          {accion === 'contacto' ? (
            <>
              <Campo id="externo-medio" etiqueta="Medio de contacto" obligatorio>
                <select
                  id="externo-medio"
                  onChange={(evento) =>
                    setMedio(evento.target.value as MedioEventoExterno)
                  }
                  value={medio}
                >
                  {MEDIOS.map((opcion) => (
                    <option key={opcion.value} value={opcion.value}>
                      {opcion.label}
                    </option>
                  ))}
                </select>
              </Campo>
              <Campo id="externo-nota" etiqueta="Nota (opcional)">
                <textarea
                  id="externo-nota"
                  onChange={(evento) => setNota(evento.target.value)}
                  rows={2}
                  value={nota}
                />
              </Campo>
            </>
          ) : null}

          {accion === 'confirmar' ? (
            <Campo
              ayuda="El costo se registra como gasto externo y solo lo ve el Dueño."
              id="externo-costo"
              etiqueta="Costo acordado"
              obligatorio
            >
              <input
                id="externo-costo"
                inputMode="decimal"
                onChange={(evento) => setCosto(evento.target.value)}
                placeholder="10.000"
                type="text"
                value={costo}
              />
            </Campo>
          ) : null}

          {accion === 'rechazar' ? (
            <Campo id="externo-motivo" etiqueta="Motivo del rechazo" obligatorio>
              <textarea
                id="externo-motivo"
                onChange={(evento) => setMotivo(evento.target.value)}
                rows={2}
                value={motivo}
              />
            </Campo>
          ) : null}

          {accion === 'reemplazar' ? (
            <Campo id="externo-reemplazo" etiqueta="Nuevo veterinario externo" obligatorio>
              <select
                id="externo-reemplazo"
                onChange={(evento) => setExternoId(evento.target.value)}
                value={externoId}
              >
                <option value="">Elegí un veterinario externo</option>
                {externos.map((empleado) => (
                  <option key={empleado.persona_id} value={empleado.persona_id}>
                    {empleado.nombre} {empleado.apellido}
                  </option>
                ))}
              </select>
            </Campo>
          ) : null}

          <div className={estilos.pieFormulario}>
            <Boton onClick={cerrar} type="button" variante="secundario">
              Cancelar
            </Boton>
            <Boton cargando={guardando} type="submit">
              Guardar
            </Boton>
          </div>
        </form>
      ) : null}
    </section>
  );
}
