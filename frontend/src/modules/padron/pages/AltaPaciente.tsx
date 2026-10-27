import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';

import {
  actualizarPaciente,
  crearPaciente,
  listarEspecies,
  listarTamanios,
  mensajeDeError,
  obtenerPaciente,
} from '../api';
import { SelectorRaza } from '../components/SelectorRaza';
import { usePuedeEscribirPadron } from '../permisos';
import type { Especie, PacienteNuevo, Tamanio } from '../tipos';
import estilos from '../padron.module.css';

function aIso(fecha: Date): string {
  const mes = String(fecha.getMonth() + 1).padStart(2, '0');
  const dia = String(fecha.getDate()).padStart(2, '0');

  return `${fecha.getFullYear()}-${mes}-${dia}`;
}

/** Convierte una edad aproximada en años a fecha de nacimiento aproximada. */
function fechaDesdeAnios(anios: number): string {
  const hoy = new Date();
  return aIso(new Date(hoy.getFullYear() - anios, hoy.getMonth(), hoy.getDate()));
}

function textoEdad(fechaIso: string): string {
  if (!fechaIso) {
    return '';
  }

  const nacimiento = new Date(`${fechaIso}T00:00:00`);
  const hoy = new Date();

  if (Number.isNaN(nacimiento.getTime()) || nacimiento > hoy) {
    return '';
  }

  let meses =
    (hoy.getFullYear() - nacimiento.getFullYear()) * 12 +
    (hoy.getMonth() - nacimiento.getMonth());

  if (hoy.getDate() < nacimiento.getDate()) {
    meses -= 1;
  }

  if (meses < 0) {
    meses = 0;
  }

  const anios = Math.floor(meses / 12);
  const restoMeses = meses % 12;
  const partes: string[] = [];

  if (anios > 0) {
    partes.push(`${anios} ${anios === 1 ? 'año' : 'años'}`);
  }

  if (restoMeses > 0) {
    partes.push(`${restoMeses} ${restoMeses === 1 ? 'mes' : 'meses'}`);
  }

  return partes.length > 0 ? partes.join(' ') : 'Menos de 1 mes';
}

export function AltaPaciente() {
  const { id } = useParams();
  const pacienteId = id ? Number(id) : null;
  const editando = pacienteId !== null;
  const [searchParams] = useSearchParams();
  const titularParam = searchParams.get('titular');
  const titularId = !editando && titularParam ? Number(titularParam) : null;
  const navigate = useNavigate();
  const puedeEscribir = usePuedeEscribirPadron();

  const [nombre, setNombre] = useState('');
  const [especieId, setEspecieId] = useState<number | null>(null);
  const [razaId, setRazaId] = useState<number | null>(null);
  const [tamanioId, setTamanioId] = useState<number | null>(null);
  const [peso, setPeso] = useState('');
  const [fecha, setFecha] = useState('');
  const [edadAprox, setEdadAprox] = useState('');
  const [castrado, setCastrado] = useState<boolean | null>(null);
  const [especies, setEspecies] = useState<Especie[]>([]);
  const [tamanios, setTamanios] = useState<Tamanio[]>([]);
  const [error, setError] = useState('');
  const [cargando, setCargando] = useState(editando);
  const [errorCarga, setErrorCarga] = useState('');
  const [enviando, setEnviando] = useState(false);
  const envioEnCurso = useRef(false);

  useEffect(() => {
    let activo = true;

    Promise.all([listarEspecies(), listarTamanios()])
      .then(([catalogoEspecies, catalogoTamanios]) => {
        if (activo) {
          setEspecies(catalogoEspecies);
          setTamanios(catalogoTamanios);
        }
      })
      .catch((fallo) => {
        if (activo) {
          setError(mensajeDeError(fallo));
        }
      });

    return () => {
      activo = false;
    };
  }, []);

  useEffect(() => {
    if (pacienteId === null) {
      return;
    }

    let activo = true;

    obtenerPaciente(pacienteId)
      .then((paciente) => {
        if (!activo) {
          return;
        }

        setErrorCarga('');
        setNombre(paciente.nombre);
        setEspecieId(paciente.especie_id);
        setRazaId(paciente.raza_id);
        setTamanioId(paciente.tamanio_id);
        setPeso(paciente.peso_kg === null ? '' : String(paciente.peso_kg));
        setFecha(paciente.fecha_nacimiento_aprox ?? '');
        setCastrado(paciente.castrado);
      })
      .catch((fallo) => {
        if (activo) {
          setErrorCarga(mensajeDeError(fallo));
        }
      })
      .finally(() => {
        if (activo) {
          setCargando(false);
        }
      });

    return () => {
      activo = false;
    };
  }, [pacienteId]);

  async function guardar(evento?: FormEvent) {
    evento?.preventDefault();

    if (envioEnCurso.current) {
      return;
    }

    const nombreLimpio = nombre.trim();

    if (!nombreLimpio) {
      setError('Ingresá el nombre de la mascota.');
      return;
    }

    if (!especieId) {
      setError('La especie es obligatoria.');
      return;
    }

    if (!editando && (!titularId || Number.isNaN(titularId))) {
      setError('Falta el titular de la mascota.');
      return;
    }

    let fechaFinal: string | null = fecha || null;

    if (!fechaFinal && edadAprox.trim()) {
      const anios = Number(edadAprox);

      if (!Number.isFinite(anios) || anios < 0) {
        setError('La edad aproximada debe ser un número de años.');
        return;
      }

      fechaFinal = fechaDesdeAnios(anios);
    }

    const datosBase: Omit<PacienteNuevo, 'titular_persona_id'> = {
      nombre: nombreLimpio,
      especie_id: especieId,
      raza_id: razaId,
      tamanio_id: tamanioId,
      peso_kg: peso.trim() || null,
      fecha_nacimiento_aprox: fechaFinal,
      castrado,
    };

    envioEnCurso.current = true;
    setEnviando(true);
    setError('');

    try {
      if (editando) {
        await actualizarPaciente(pacienteId, datosBase);
        navigate(`/padron/paciente/${pacienteId}`);
      } else {
        await crearPaciente({ ...datosBase, titular_persona_id: titularId as number });
        navigate(`/padron/persona/${titularId}`);
      }
    } catch (fallo) {
      setError(mensajeDeError(fallo));
    } finally {
      envioEnCurso.current = false;
      setEnviando(false);
    }
  }

  if (!puedeEscribir) {
    return (
      <section className={estilos.pagina}>
        <p className={estilos.cargando}>No tenés permiso para modificar el padrón.</p>
        <Link className={estilos.enlace} to="/padron">
          Volver a la búsqueda
        </Link>
      </section>
    );
  }

  if (cargando) {
    return (
      <section className={estilos.pagina}>
        <p className={estilos.cargando} role="status">
          Cargando datos…
        </p>
      </section>
    );
  }

  if (errorCarga) {
    return (
      <section className={estilos.pagina}>
        <div className={estilos.error} role="alert">
          <p>{errorCarga}</p>
        </div>
        <Link className={estilos.enlace} to="/padron">
          Volver a la búsqueda
        </Link>
      </section>
    );
  }

  const edadCalculada = textoEdad(fecha);

  return (
    <section className={estilos.pagina} aria-labelledby="titulo-alta-paciente">
      <div>
        <h1 className={estilos.titulo} id="titulo-alta-paciente">
          {editando ? 'Editar mascota' : 'Alta de mascota'}
        </h1>
        <p className={estilos.subtitulo}>
          La especie es obligatoria. La raza y el tamaño son opcionales.
        </p>
      </div>

      <form className={estilos.formulario} onSubmit={guardar}>
        <div className={estilos.campo}>
          <label htmlFor="paciente-nombre">Nombre</label>
          <input
            id="paciente-nombre"
            onChange={(evento) => setNombre(evento.target.value)}
            required
            type="text"
            value={nombre}
          />
        </div>

        <div className={estilos.campo}>
          <label htmlFor="paciente-especie">Especie</label>
          <select
            id="paciente-especie"
            onChange={(evento) => {
              setEspecieId(evento.target.value ? Number(evento.target.value) : null);
              setRazaId(null);
            }}
            required
            value={especieId ?? ''}
          >
            <option value="">Seleccionar especie</option>
            {especies.map((especie) => (
              <option key={especie.id} value={especie.id}>
                {especie.nombre}
              </option>
            ))}
          </select>
        </div>

        <div className={estilos.campo}>
          <label htmlFor="raza">Raza</label>
          <SelectorRaza
            especieId={especieId}
            onChange={setRazaId}
            puedeEscribir={puedeEscribir}
            value={razaId}
          />
        </div>

        <div className={`${estilos.grilla} ${estilos.grillaDos}`}>
          <div className={estilos.campo}>
            <label htmlFor="paciente-tamanio">Tamaño</label>
            <select
              id="paciente-tamanio"
              onChange={(evento) =>
                setTamanioId(evento.target.value ? Number(evento.target.value) : null)
              }
              value={tamanioId ?? ''}
            >
              <option value="">Sin tamaño</option>
              {tamanios.map((tamanio) => (
                <option key={tamanio.id} value={tamanio.id}>
                  {tamanio.nombre}
                </option>
              ))}
            </select>
          </div>

          <div className={estilos.campo}>
            <label htmlFor="paciente-peso">Peso (kg)</label>
            <input
              id="paciente-peso"
              inputMode="decimal"
              min="0"
              onChange={(evento) => setPeso(evento.target.value)}
              step="0.01"
              type="number"
              value={peso}
            />
          </div>
        </div>

        <div className={estilos.campo}>
          <label htmlFor="paciente-fecha">Fecha de nacimiento aproximada</label>
          <input
            id="paciente-fecha"
            onChange={(evento) => setFecha(evento.target.value)}
            type="date"
            value={fecha}
          />
          <p className={estilos.ayuda}>
            Se guarda la fecha aproximada. La edad se calcula sola y no se edita.
          </p>
        </div>

        <div className={estilos.campo}>
          <label htmlFor="paciente-edad">Edad aproximada (años)</label>
          <input
            id="paciente-edad"
            inputMode="numeric"
            min="0"
            onChange={(evento) => setEdadAprox(evento.target.value)}
            placeholder="Opcional: si no sabés la fecha"
            step="1"
            type="number"
            value={edadAprox}
          />
          <p className={estilos.ayuda}>
            Si la cargás, se convierte a fecha de nacimiento aproximada.
          </p>
        </div>

        <div className={estilos.campo}>
          <label htmlFor="paciente-edad-calculada">Edad calculada</label>
          <output className={estilos.dato} id="paciente-edad-calculada">
            {edadCalculada || 'Se calcula al guardar la fecha'}
          </output>
        </div>

        <div className={estilos.campo}>
          <label htmlFor="paciente-castrado">Castrado</label>
          <select
            id="paciente-castrado"
            onChange={(evento) =>
              setCastrado(
                evento.target.value === '' ? null : evento.target.value === 'si',
              )
            }
            value={castrado === null ? '' : castrado ? 'si' : 'no'}
          >
            <option value="">Sin dato</option>
            <option value="si">Sí</option>
            <option value="no">No</option>
          </select>
        </div>

        {error ? (
          <p className={estilos.error} role="alert">
            {error}
          </p>
        ) : null}

        <div className={estilos.pie}>
          <button className={estilos.boton} disabled={enviando} type="submit">
            {enviando ? 'Guardando…' : 'Guardar'}
          </button>
          <Link
            className={`${estilos.boton} ${estilos.botonSecundario}`}
            to={editando ? `/padron/paciente/${pacienteId}` : '/padron'}
          >
            Cancelar
          </Link>
        </div>
      </form>
    </section>
  );
}
