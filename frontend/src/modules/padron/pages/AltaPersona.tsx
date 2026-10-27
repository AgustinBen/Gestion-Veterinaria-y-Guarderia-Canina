import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import {
  actualizarPersona,
  crearPersona,
  leerErrorDuplicado,
  mensajeDeError,
  obtenerPersona,
} from '../api';
import { ModalDuplicado } from '../components/ModalDuplicado';
import type { CoincidenciaDuplicado, PersonaDetalle, PersonaResumen } from '../tipos';
import estilos from '../padron.module.css';

type Valores = {
  nombre: string;
  apellido: string;
  dni: string;
  telefonos: string;
  calle: string;
  numero: string;
  localidad: string;
  referencia: string;
};

const VALORES_VACIOS: Valores = {
  nombre: '',
  apellido: '',
  dni: '',
  telefonos: '',
  calle: '',
  numero: '',
  localidad: '',
  referencia: '',
};

function valoresDePersona(persona: PersonaDetalle): Valores {
  return {
    nombre: persona.nombre,
    apellido: persona.apellido,
    dni: persona.dni ?? '',
    telefonos: persona.telefonos.join(', '),
    calle: persona.domicilio?.calle ?? '',
    numero: persona.domicilio?.numero === null ? '' : String(persona.domicilio?.numero ?? ''),
    localidad: persona.domicilio?.localidad ?? '',
    referencia: persona.domicilio?.referencia ?? '',
  };
}

export function AltaPersona() {
  const { id } = useParams();
  const personaId = id ? Number(id) : null;
  const editando = personaId !== null;
  const navigate = useNavigate();

  const [valores, setValores] = useState<Valores>(VALORES_VACIOS);
  const [personaDuplicada, setPersonaDuplicada] = useState<PersonaResumen | null>(null);
  const [coincidencias, setCoincidencias] = useState<CoincidenciaDuplicado[]>([]);
  const [modalAbierto, setModalAbierto] = useState(false);
  const [error, setError] = useState('');
  const [cargando, setCargando] = useState(editando);
  const [errorCarga, setErrorCarga] = useState('');
  const [enviando, setEnviando] = useState(false);
  const envioEnCurso = useRef(false);

  useEffect(() => {
    if (personaId === null) {
      return;
    }

    let activo = true;

    obtenerPersona(personaId)
      .then((persona) => {
        if (activo) {
          setErrorCarga('');
          setValores(valoresDePersona(persona));
        }
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
  }, [personaId]);

  function cambiar(campo: keyof Valores, valor: string) {
    setValores((previos) => ({ ...previos, [campo]: valor }));
  }

  async function guardar(evento?: FormEvent, confirmarDuplicado = false) {
    evento?.preventDefault();

    if (envioEnCurso.current) {
      return;
    }

    const nombre = valores.nombre.trim();
    const apellido = valores.apellido.trim();
    const dni = valores.dni.trim();
    const calle = valores.calle.trim();
    const localidad = valores.localidad.trim();
    const telefonos = valores.telefonos
      .split(',')
      .map((telefono) => telefono.trim())
      .filter(Boolean);

    if (!nombre || !apellido || !dni) {
      setError('Completá nombre, apellido y DNI.');
      return;
    }

    if (telefonos.length === 0) {
      setError('Ingresá al menos un teléfono.');
      return;
    }

    if ((calle && !localidad) || (!calle && localidad)) {
      setError('Para cargar el domicilio completá calle y localidad.');
      return;
    }

    const numero = valores.numero.trim() ? Number(valores.numero) : null;

    if (numero !== null && !Number.isFinite(numero)) {
      setError('El número de domicilio debe ser numérico.');
      return;
    }

    const domicilio = calle
      ? {
          calle,
          numero,
          localidad,
          referencia: valores.referencia.trim() || null,
        }
      : undefined;

    envioEnCurso.current = true;
    setEnviando(true);
    setError('');
    setPersonaDuplicada(null);

    try {
      const datos = {
        nombre,
        apellido,
        dni,
        telefonos,
        ...(domicilio ? { domicilio } : {}),
        ...(confirmarDuplicado ? { confirmar_duplicado: true } : {}),
      };
      const persona = editando
        ? await actualizarPersona(personaId, datos)
        : await crearPersona(datos);

      navigate(editando ? `/padron/persona/${persona.id}` : '/padron');
    } catch (fallo) {
      const duplicado = leerErrorDuplicado(fallo);

      if (duplicado?.codigo === 'DNI_DUPLICADO') {
        setCoincidencias([]);
        setModalAbierto(false);
        setPersonaDuplicada(duplicado.persona);
      } else if (duplicado?.codigo === 'POSIBLE_DUPLICADO') {
        setPersonaDuplicada(null);
        setCoincidencias(duplicado.coincidencias);
        setModalAbierto(true);
      } else {
        setError(mensajeDeError(fallo));
      }
    } finally {
      envioEnCurso.current = false;
      setEnviando(false);
    }
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

  return (
    <section className={estilos.pagina} aria-labelledby="titulo-alta-persona">
      <div>
        <h1 className={estilos.titulo} id="titulo-alta-persona">
          {editando ? 'Editar dueño' : 'Alta de dueño'}
        </h1>
        <p className={estilos.subtitulo}>
          DNI, nombre, apellido y teléfono son obligatorios. El domicilio es opcional.
        </p>
      </div>

      <form className={estilos.formulario} onSubmit={guardar}>
        <div className={`${estilos.grilla} ${estilos.grillaDos}`}>
          <div className={estilos.campo}>
            <label htmlFor="persona-nombre">Nombre</label>
            <input
              id="persona-nombre"
              onChange={(evento) => cambiar('nombre', evento.target.value)}
              required
              type="text"
              value={valores.nombre}
            />
          </div>

          <div className={estilos.campo}>
            <label htmlFor="persona-apellido">Apellido</label>
            <input
              id="persona-apellido"
              onChange={(evento) => cambiar('apellido', evento.target.value)}
              required
              type="text"
              value={valores.apellido}
            />
          </div>
        </div>

        <div className={estilos.campo}>
          <label htmlFor="persona-dni">DNI</label>
          <input
            id="persona-dni"
            inputMode="numeric"
            onChange={(evento) => cambiar('dni', evento.target.value)}
            required
            type="text"
            value={valores.dni}
          />
        </div>

        <div className={estilos.campo}>
          <label htmlFor="persona-telefonos">Teléfonos</label>
          <input
            id="persona-telefonos"
            onChange={(evento) => cambiar('telefonos', evento.target.value)}
            placeholder="Separados por coma"
            required
            type="text"
            value={valores.telefonos}
          />
        </div>

        <fieldset className={estilos.tarjeta}>
          <legend className={estilos.etiqueta}>Domicilio (opcional)</legend>

          <div className={`${estilos.grilla} ${estilos.grillaDos}`}>
            <div className={estilos.campo}>
              <label htmlFor="persona-calle">Calle</label>
              <input
                id="persona-calle"
                onChange={(evento) => cambiar('calle', evento.target.value)}
                type="text"
                value={valores.calle}
              />
            </div>

            <div className={estilos.campo}>
              <label htmlFor="persona-numero">Número</label>
              <input
                id="persona-numero"
                inputMode="numeric"
                onChange={(evento) => cambiar('numero', evento.target.value)}
                type="text"
                value={valores.numero}
              />
            </div>

            <div className={estilos.campo}>
              <label htmlFor="persona-localidad">Localidad</label>
              <input
                id="persona-localidad"
                onChange={(evento) => cambiar('localidad', evento.target.value)}
                type="text"
                value={valores.localidad}
              />
            </div>

            <div className={estilos.campo}>
              <label htmlFor="persona-referencia">Referencia</label>
              <input
                id="persona-referencia"
                onChange={(evento) => cambiar('referencia', evento.target.value)}
                type="text"
                value={valores.referencia}
              />
            </div>
          </div>
        </fieldset>

        {personaDuplicada ? (
          <p className={estilos.error} role="alert">
            Ya existe una persona con ese DNI. No se puede crear otra.
            <Link className={estilos.enlace} to={`/padron/persona/${personaDuplicada.id}`}>
              Ver ficha existente
            </Link>
          </p>
        ) : null}

        {error ? (
          <p className={estilos.error} role="alert">
            {error}
          </p>
        ) : null}

        <div className={estilos.pie}>
          <button className={estilos.boton} disabled={enviando} type="submit">
            {enviando ? 'Guardando…' : 'Guardar'}
          </button>
          <Link className={`${estilos.boton} ${estilos.botonSecundario}`} to="/padron">
            Cancelar
          </Link>
        </div>
      </form>

      <ModalDuplicado
        abierto={modalAbierto}
        coincidencias={coincidencias}
        onAbrirFicha={(personaElegida) => {
          setModalAbierto(false);
          navigate(`/padron/persona/${personaElegida}`);
        }}
        onCerrar={() => setModalAbierto(false)}
        onCrearIgual={() => {
          setModalAbierto(false);
          void guardar(undefined, true);
        }}
      />
    </section>
  );
}
