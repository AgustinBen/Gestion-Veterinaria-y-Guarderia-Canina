import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { Alerta } from '../../../core/components/ui/Alerta';
import { Boton } from '../../../core/components/ui/Boton';
import { Campo } from '../../../core/components/ui/Campo';
import { buscarPersonas, mensajeDeError } from '../api';
import { usePuedeVerDeudores } from '../permisos';
import type { PersonaBusqueda } from '../tipos';
import estilos from '../cobros.module.css';

/** Retraso corto para no saturar la API mientras se escribe. */
const RETRASO_BUSQUEDA_MS = 250;
const MAX_RESULTADOS = 10;

type Estado = 'cargando' | 'listo' | 'error';

type Consulta = {
  texto: string;
  estado: Estado;
  filas: PersonaBusqueda[];
  error: string;
};

/** Pantalla de entrada de cobros: buscar el cliente y abrir su cuenta. */
export function Cobrar() {
  const [texto, setTexto] = useState('');
  const [reintento, setReintento] = useState(0);
  const [consultaAplicada, setConsultaAplicada] = useState<Consulta | null>(null);
  const puedeVerDeudores = usePuedeVerDeudores();

  const consulta = texto.trim();
  // Solo se muestra el resultado de la consulta vigente; al cambiar el texto
  // vuelve a "cargando" sin tocar estado desde el efecto.
  const vigente = consultaAplicada?.texto === consulta ? consultaAplicada : null;
  const estado: Estado | null = !consulta ? null : (vigente?.estado ?? 'cargando');
  const resultados = vigente?.filas ?? [];
  const error = vigente?.error ?? '';

  useEffect(() => {
    const busqueda = texto.trim();

    if (!busqueda) {
      return;
    }

    const control = new AbortController();
    const temporizador = window.setTimeout(async () => {
      setConsultaAplicada({ texto: busqueda, estado: 'cargando', filas: [], error: '' });

      try {
        const personas = await buscarPersonas(busqueda, { signal: control.signal });

        if (control.signal.aborted) {
          return;
        }

        setConsultaAplicada({
          texto: busqueda,
          estado: 'listo',
          filas: personas.slice(0, MAX_RESULTADOS),
          error: '',
        });
      } catch (fallo) {
        if (control.signal.aborted) {
          return;
        }

        setConsultaAplicada({
          texto: busqueda,
          estado: 'error',
          filas: [],
          error: mensajeDeError(fallo),
        });
      }
    }, RETRASO_BUSQUEDA_MS);

    return () => {
      window.clearTimeout(temporizador);
      control.abort();
    };
  }, [texto, reintento]);

  return (
    <section className={estilos.pagina} aria-labelledby="titulo-cobros">
      <div className={estilos.cabecera}>
        <div>
          <h1 className={estilos.titulo} id="titulo-cobros">
            Cobros
          </h1>
          <p className={estilos.subtitulo}>
            Buscá al cliente para cobrar, registrar una seña o ver su saldo.
          </p>
        </div>

        {puedeVerDeudores ? (
          <div className={estilos.acciones}>
            <Link className={estilos.botonEnlaceSecundario} to="/cobros/deudores">
              Ver deudores
            </Link>
          </div>
        ) : null}
      </div>

      <Campo etiqueta="Buscar cliente" id="cobros-busqueda">
        <input
          autoComplete="off"
          id="cobros-busqueda"
          onChange={(evento) => setTexto(evento.target.value)}
          placeholder="Ej.: Ana, 30111222, 1144556677"
          type="search"
          value={texto}
        />
      </Campo>

      {estado === 'cargando' ? (
        <p className={estilos.cargando} role="status">
          Buscando clientes…
        </p>
      ) : null}

      {estado === 'error' ? (
        <Alerta
          acciones={
            <Boton
              onClick={() => setReintento((valor) => valor + 1)}
              variante="secundario"
            >
              Reintentar
            </Boton>
          }
          role="alert"
          tono="error"
        >
          {error}
        </Alerta>
      ) : null}

      {estado === 'listo' && resultados.length === 0 ? (
        <p className={estilos.vacio}>No encontramos clientes con ese dato.</p>
      ) : null}

      {resultados.length > 0 ? (
        <ul className={estilos.resultados}>
          {resultados.map((persona) => (
            <li key={persona.id}>
              <Link className={estilos.resultado} to={`/cobros/cliente/${persona.id}`}>
                <span className={estilos.filaResultado}>
                  <strong className={estilos.resultadoNombre}>
                    {persona.apellido}, {persona.nombre}
                  </strong>
                  {persona.dni_pendiente ? (
                    <span className={`${estilos.insignia} ${estilos.insigniaAviso}`}>
                      DNI pendiente
                    </span>
                  ) : null}
                </span>

                <span className={estilos.textoSuave}>
                  {persona.dni ? `DNI ${persona.dni}` : 'Sin DNI registrado'}
                  {persona.telefonos.length > 0
                    ? ` · Tel. ${persona.telefonos.join(' · ')}`
                    : ''}
                </span>

                <span className={estilos.enlace}>Ver cuenta y cobrar</span>
              </Link>
            </li>
          ))}
        </ul>
      ) : null}

      {!consulta ? (
        <p className={estilos.ayudaPagina}>
          Buscá un dueño por nombre, DNI o teléfono. La deuda se calcula sola a
          partir de los cargos y los pagos.
        </p>
      ) : null}
    </section>
  );
}
