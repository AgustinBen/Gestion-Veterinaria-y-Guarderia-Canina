import { useEffect, useRef, useState, type FormEvent } from 'react';

import { Alerta } from '../../../core/components/ui/Alerta';
import { Boton } from '../../../core/components/ui/Boton';
import { Campo } from '../../../core/components/ui/Campo';
import { formatearDinero, formatearMonto, parsearDinero } from '../../../core/formatos/dinero';
import {
  generarIdempotencyKey,
  listarMediosPago,
  mensajeDeError,
  mensajeDeSaldoRestante,
  registrarPago,
  saldoRestanteDeError,
} from '../api';
import type { CargoDetalle, MedioPago, Pago } from '../tipos';
import estilos from '../cobros.module.css';

type Props = {
  cargo: CargoDetalle;
  onPagado: (pago: Pago) => void;
  onCancelar: () => void;
};

type EstadoMedios = {
  estado: 'cargando' | 'listo' | 'error';
  medios: MedioPago[];
  error: string;
};

const ID_MONTO = 'pago-monto';
const ID_MEDIO = 'pago-medio';
const ID_SENA = 'pago-sena';

/**
 * Registro de un pago (RN-20). El monto sugerido es el saldo, pero se puede
 * editar. La deuda la calcula siempre el backend: acá no se guarda ningún
 * saldo, solo se muestra lo que la API devuelve.
 */
export function FormularioPago({ cargo, onPagado, onCancelar }: Props) {
  const [medios, setMedios] = useState<EstadoMedios>({
    estado: 'cargando',
    medios: [],
    error: '',
  });
  const [reintentoMedios, setReintentoMedios] = useState(0);
  const [montoTexto, setMontoTexto] = useState(() => formatearMonto(cargo.saldo));
  const [medio, setMedio] = useState('');
  const [esSena, setEsSena] = useState(false);
  const [errorMonto, setErrorMonto] = useState('');
  const [errorEnvio, setErrorEnvio] = useState('');
  const [enviando, setEnviando] = useState(false);

  // La clave se genera una sola vez por apertura del formulario. Si la red
  // falla y la persona reintenta, se reutiliza para no registrar el pago dos
  // veces.
  const [idempotencyKey] = useState(() => generarIdempotencyKey());
  // El estado de React no alcanza para frenar un doble clic: se marca de forma
  // sincrónica antes de esperar la respuesta.
  const enviandoRef = useRef(false);

  useEffect(() => {
    const control = new AbortController();
    let activo = true;

    listarMediosPago({ signal: control.signal })
      .then((lista) => {
        if (!activo || control.signal.aborted) {
          return;
        }

        setMedios({ estado: 'listo', medios: lista, error: '' });
        setMedio((actual) => {
          if (actual) {
            return actual;
          }

          const primero = lista.find((item) => item.activo) ?? lista[0];

          return primero?.codigo ?? '';
        });
      })
      .catch((fallo) => {
        if (!activo || control.signal.aborted) {
          return;
        }

        setMedios({
          estado: 'error',
          medios: [],
          error: mensajeDeError(fallo),
        });
      });

    return () => {
      activo = false;
      control.abort();
    };
  }, [reintentoMedios]);

  async function registrar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();

    if (enviandoRef.current) {
      return;
    }

    let montoCentavos: number;

    try {
      montoCentavos = parsearDinero(montoTexto);
    } catch (fallo) {
      setErrorMonto(fallo instanceof Error ? fallo.message : 'Monto inválido.');
      return;
    }

    if (!medio) {
      setErrorEnvio('Elegí un medio de pago.');
      return;
    }

    setErrorMonto('');
    setErrorEnvio('');
    enviandoRef.current = true;
    setEnviando(true);

    try {
      const pago = await registrarPago(
        cargo.id,
        { monto_centavos: montoCentavos, medio, es_sena: esSena },
        { idempotencyKey },
      );

      onPagado(pago);
    } catch (fallo) {
      const saldoRestante = saldoRestanteDeError(fallo);

      setErrorEnvio(
        saldoRestante !== null
          ? mensajeDeSaldoRestante(saldoRestante)
          : mensajeDeError(fallo),
      );
    } finally {
      enviandoRef.current = false;
      setEnviando(false);
    }
  }

  if (medios.estado === 'cargando') {
    return (
      <p className={estilos.cargando} role="status">
        Cargando medios de pago…
      </p>
    );
  }

  if (medios.estado === 'error') {
    return (
      <Alerta
        acciones={
          <Boton
            onClick={() => setReintentoMedios((valor) => valor + 1)}
            variante="secundario"
          >
            Reintentar
          </Boton>
        }
        role="alert"
        tono="error"
      >
        {medios.error}
      </Alerta>
    );
  }

  return (
    <form className={estilos.formulario} onSubmit={registrar}>
      <p className={estilos.textoSuave}>
        Saldo pendiente: <strong>{formatearDinero(cargo.saldo)}</strong>
      </p>

      <Campo
        ayuda="Podés ajustarlo. Por ejemplo: 10.000 o 10.000,50."
        error={errorMonto}
        etiqueta="Monto"
        id={ID_MONTO}
      >
        <input
          autoComplete="off"
          id={ID_MONTO}
          inputMode="decimal"
          onChange={(evento) => {
            setMontoTexto(evento.target.value);
            setErrorMonto('');
          }}
          value={montoTexto}
        />
      </Campo>

      <Campo etiqueta="Medio de pago" id={ID_MEDIO}>
        <select
          id={ID_MEDIO}
          onChange={(evento) => setMedio(evento.target.value)}
          value={medio}
        >
          {medios.medios.map((item) => (
            <option disabled={!item.activo} key={item.codigo} value={item.codigo}>
              {item.nombre}
            </option>
          ))}
        </select>
      </Campo>

      <label className={estilos.check} htmlFor={ID_SENA}>
        <input
          checked={esSena}
          id={ID_SENA}
          onChange={(evento) => setEsSena(evento.target.checked)}
          type="checkbox"
        />
        Es seña
      </label>

      {errorEnvio ? (
        <Alerta role="alert" tono="error">
          {errorEnvio}
        </Alerta>
      ) : null}

      <div className={estilos.acciones}>
        <Boton onClick={onCancelar} variante="secundario">
          Cancelar
        </Boton>
        <Boton cargando={enviando} type="submit">
          Registrar pago
        </Boton>
      </div>
    </form>
  );
}
