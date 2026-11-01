import { useEffect, useRef, useState } from 'react';

import { Selector } from '../../../core/components/ui/Selector';
import { crearRaza, listarRazas, mensajeDeError } from '../api';
import type { Raza } from '../tipos';
import estilos from '../padron.module.css';

type Props = {
  especieId: number | null;
  value: number | null;
  onChange: (razaId: number | null) => void;
  puedeEscribir: boolean;
};

export function SelectorRaza({ especieId, value, onChange, puedeEscribir }: Props) {
  const [razas, setRazas] = useState<Raza[]>([]);
  const [nueva, setNueva] = useState('');
  const [creando, setCreando] = useState(false);
  const [error, setError] = useState('');
  const envioEnCurso = useRef(false);

  useEffect(() => {
    if (!especieId) {
      return;
    }

    let activo = true;

    listarRazas(especieId)
      .then((catalogo) => {
        if (activo) {
          setError('');
          setRazas(catalogo);
        }
      })
      .catch((fallo) => {
        if (activo) {
          setRazas([]);
          setError(mensajeDeError(fallo));
        }
      });

    return () => {
      activo = false;
    };
  }, [especieId]);

  // Se filtra por especie para no mostrar razas de otra especie al cambiarla.
  const razasVisibles = razas.filter((raza) => raza.especie_id === especieId);

  async function crear() {
    if (!especieId || !nueva.trim() || !puedeEscribir || envioEnCurso.current) {
      return;
    }

    envioEnCurso.current = true;
    setCreando(true);
    setError('');

    try {
      const raza = await crearRaza({ nombre: nueva.trim(), especie_id: especieId });
      setRazas((previas) =>
        previas.some((existente) => existente.id === raza.id) ? previas : [...previas, raza],
      );
      onChange(raza.id);
      setNueva('');
    } catch (fallo) {
      setError(mensajeDeError(fallo));
    } finally {
      envioEnCurso.current = false;
      setCreando(false);
    }
  }

  return (
    <div className={estilos.selectorRaza}>
      <Selector
        ariaLabel="Raza"
        disabled={!especieId}
        id="raza"
        onChange={(valor) => onChange(valor ? Number(valor) : null)}
        opciones={razasVisibles.map((raza) => ({
          value: String(raza.id),
          label: raza.nombre,
        }))}
        placeholder="Sin raza"
        value={value === null ? '' : String(value)}
      />

      {puedeEscribir && especieId ? (
        <div className={estilos.altaRaza}>
          <input
            aria-label="Nueva raza"
            onChange={(evento) => setNueva(evento.target.value)}
            placeholder="Alta rápida de raza"
            type="text"
            value={nueva}
          />
          <button
            className={`${estilos.boton} ${estilos.botonSecundario}`}
            disabled={creando || !nueva.trim()}
            onClick={crear}
            type="button"
          >
            {creando ? 'Creando…' : 'Crear raza'}
          </button>
        </div>
      ) : null}

      {error ? (
        <p className={estilos.error} role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
