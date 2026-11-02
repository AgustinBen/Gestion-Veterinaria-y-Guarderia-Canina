import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { useAuth } from '../../../core/auth/contexto';
import { Alerta } from '../../../core/components/ui/Alerta';
import { Boton } from '../../../core/components/ui/Boton';
import { listarEmpleados, obtenerPaciente } from '../../padron/api';
import type { EmpleadoDetalle, PacienteDetalle } from '../../padron/tipos';
import {
  listarAtenciones,
  mensajeDeError,
  obtenerAtencion,
  obtenerLibreta,
} from '../api';
import { DuenioMascota } from '../components/DuenioMascota';
import { FormularioAtencion } from '../components/FormularioAtencion';
import { LibretaVacunas } from '../components/LibretaVacunas';
import { SubidaPlacas } from '../components/SubidaPlacas';
import { formatearFechaHora } from '../fechas';
import { puedeEscribirHistoria } from '../permisos';
import type {
  AtencionDetalle,
  AtencionResumen,
  CategoriaClinica,
  LibretaVacunasItem,
  TipoAtencion,
} from '../tipos';
import estilos from '../clinica.module.css';

const ETIQUETA_TIPO: Record<TipoAtencion, string> = {
  CONSULTA: 'Consulta',
  VACUNA: 'Vacuna',
  CIRUGIA: 'Cirugía',
  TRATAMIENTO: 'Tratamiento',
  ESTUDIO: 'Estudio',
};

const FILTROS: { id: 'TODAS' | CategoriaClinica; etiqueta: string }[] = [
  { id: 'TODAS', etiqueta: 'Todas' },
  { id: 'CONSULTA', etiqueta: 'Consultas' },
  { id: 'VACUNA', etiqueta: 'Vacunas' },
  { id: 'CIRUGIA', etiqueta: 'Cirugías' },
  { id: 'TRATAMIENTO', etiqueta: 'Tratamientos' },
];

const MAX_ATENCIONES = 100;

type Estado = 'cargando' | 'listo' | 'error';

function textoEdad(paciente: PacienteDetalle): string {
  if (paciente.edad_anios === null && paciente.edad_meses === null) {
    return 'Sin fecha de nacimiento';
  }

  const partes: string[] = [];

  if (paciente.edad_anios !== null && paciente.edad_anios > 0) {
    partes.push(
      `${paciente.edad_anios} ${paciente.edad_anios === 1 ? 'año' : 'años'}`,
    );
  }

  if (paciente.edad_meses !== null && paciente.edad_meses > 0) {
    partes.push(
      `${paciente.edad_meses} ${paciente.edad_meses === 1 ? 'mes' : 'meses'}`,
    );
  }

  return partes.length > 0 ? partes.join(' ') : 'Menos de 1 mes';
}

export function HistoriaClinica() {
  const { pacienteId } = useParams();
  const id = Number(pacienteId);
  const { sesion } = useAuth();
  const puedeEscribir = puedeEscribirHistoria(sesion?.rol ?? null);
  const [paciente, setPaciente] = useState<PacienteDetalle | null>(null);
  const [empleados, setEmpleados] = useState<EmpleadoDetalle[]>([]);
  const [atenciones, setAtenciones] = useState<AtencionResumen[]>([]);
  const [vacunas, setVacunas] = useState<LibretaVacunasItem[]>([]);
  const [estado, setEstado] = useState<Estado>('cargando');
  const [error, setError] = useState('');
  const [intento, setIntento] = useState(0);
  const [filtro, setFiltro] = useState<'TODAS' | CategoriaClinica>('TODAS');
  const [mostrandoFormulario, setMostrandoFormulario] = useState(false);
  const [rectificando, setRectificando] = useState<AtencionDetalle | null>(null);
  const [errorAccion, setErrorAccion] = useState('');

  useEffect(() => {
    const controlador = new AbortController();
    let activo = true;

    async function cargar() {
      if (!Number.isInteger(id) || id <= 0) {
        setError('La mascota indicada no es válida.');
        setEstado('error');
        return;
      }

      setEstado('cargando');
      setError('');

      try {
        const [datosPaciente, datosEmpleados, datosAtenciones, datosVacunas] =
          await Promise.all([
            obtenerPaciente(id, { signal: controlador.signal }),
            listarEmpleados({ signal: controlador.signal }),
            listarAtenciones(id, {
              limite: MAX_ATENCIONES,
              signal: controlador.signal,
            }),
            obtenerLibreta(id, { signal: controlador.signal }),
          ]);

        if (activo) {
          setPaciente(datosPaciente);
          setEmpleados(datosEmpleados);
          setAtenciones(datosAtenciones);
          setVacunas(datosVacunas);
          setEstado('listo');
        }
      } catch (fallo) {
        if (!activo || controlador.signal.aborted) {
          return;
        }

        setError(mensajeDeError(fallo));
        setEstado('error');
      }
    }

    void cargar();

    return () => {
      activo = false;
      controlador.abort();
    };
  }, [id, intento]);

  function recargar() {
    setIntento((actual) => actual + 1);
  }

  function guardado() {
    setErrorAccion('');
    setMostrandoFormulario(false);
    setRectificando(null);
    recargar();
  }

  async function abrirRectificacion(atencion: AtencionResumen) {
    setErrorAccion('');
    setMostrandoFormulario(false);

    try {
      const detalle = await obtenerAtencion(atencion.id);
      setRectificando(detalle);
    } catch (fallo) {
      setErrorAccion(mensajeDeError(fallo));
    }
  }

  const visibles =
    filtro === 'TODAS'
      ? atenciones
      : atenciones.filter((atencion) => atencion.tipo === filtro);

  return (
    <section className={estilos.pagina} aria-labelledby="titulo-mascota">
      <header className={estilos.cabecera}>
        <div className={estilos.introduccion}>
          <p className={estilos.antetitulo}>Ficha completa</p>
          <h1 className={estilos.titulo} id="titulo-mascota">
            {paciente?.nombre ?? 'Historia clínica'}
          </h1>
          {paciente ? (
            <p className={estilos.meta}>
              <span>{paciente.especie_nombre}</span>
              {paciente.raza_nombre ? <span>{paciente.raza_nombre}</span> : null}
              <span>{textoEdad(paciente)}</span>
              <DuenioMascota pacienteId={paciente.id} />
            </p>
          ) : null}
          <p className={estilos.subtitulo}>
            Consultas, vacunas, cirugías, tratamientos y estudios de la mascota.
          </p>
        </div>

        <div className={estilos.acciones}>
          <Link className={estilos.enlace} to="/historia-clinica">
            Volver a mascotas
          </Link>
          {!puedeEscribir ? (
            <span className={estilos.insignia}>Solo lectura</span>
          ) : null}
        </div>
      </header>

      {estado === 'cargando' ? (
        <section className={estilos.panel}>
          <p className={estilos.cargando}>Cargando historia clínica…</p>
        </section>
      ) : estado === 'error' ? (
        <section className={estilos.panel}>
          <Alerta
            acciones={
              <Boton onClick={recargar} variante="secundario">
                Reintentar
              </Boton>
            }
            role="alert"
            tono="error"
          >
            {error}
          </Alerta>
        </section>
      ) : paciente ? (
        <>
          {errorAccion ? (
            <Alerta role="alert" tono="error">
              {errorAccion}
            </Alerta>
          ) : null}

          {puedeEscribir ? (
            <div className={estilos.acciones}>
              <Boton
                onClick={() => {
                  setRectificando(null);
                  setMostrandoFormulario((actual) => !actual);
                }}
                variante={mostrandoFormulario ? 'secundario' : 'primario'}
              >
                {mostrandoFormulario ? 'Cerrar formulario' : 'Registrar atención'}
              </Boton>
            </div>
          ) : null}

          {puedeEscribir && (mostrandoFormulario || rectificando) ? (
            <section className={estilos.panel}>
              <FormularioAtencion
                atencion={rectificando}
                empleados={empleados}
                onCancelar={() => {
                  setMostrandoFormulario(false);
                  setRectificando(null);
                }}
                onGuardado={guardado}
                pacienteId={paciente.id}
              />
            </section>
          ) : null}

          <section className={estilos.panel} aria-labelledby="atenciones-titulo">
            <div className={estilos.panelCabecera}>
              <h2 className={estilos.panelTitulo} id="atenciones-titulo">
                Atenciones
              </h2>
              <span className={estilos.etiqueta}>{atenciones.length} registradas</span>
            </div>

            <div className={estilos.chips} aria-label="Filtrar atenciones">
              {FILTROS.map((opcion) => (
                <button
                  aria-pressed={filtro === opcion.id}
                  className={`${estilos.chip} ${
                    filtro === opcion.id ? estilos.chipActivo : ''
                  }`.trim()}
                  key={opcion.id}
                  onClick={() => setFiltro(opcion.id)}
                  type="button"
                >
                  {opcion.etiqueta}
                </button>
              ))}
            </div>

            {visibles.length === 0 ? (
              <p className={estilos.vacio}>
                {atenciones.length === 0
                  ? 'Todavía no hay atenciones registradas.'
                  : 'No hay atenciones de esta categoría.'}
              </p>
            ) : (
              <ul className={estilos.lista}>
                {visibles.map((atencion) => (
                  <li className={estilos.tarjeta} key={atencion.id}>
                    <div className={estilos.tarjetaCabecera}>
                      <strong className={estilos.tarjetaTitulo}>
                        {ETIQUETA_TIPO[atencion.tipo]} · #{atencion.id}
                      </strong>
                      <span className={estilos.etiqueta}>
                        {formatearFechaHora(atencion.fecha_hora)}
                      </span>
                    </div>

                    <div className={estilos.meta}>
                      <span>
                        Veterinario:{' '}
                        <strong>
                          {atencion.veterinario_nombre ?? 'sin asignar'}
                        </strong>
                      </span>
                      {atencion.cirujano_externo_nombre ? (
                        <span>
                          Cirujano:{' '}
                          <strong>{atencion.cirujano_externo_nombre}</strong>
                        </span>
                      ) : null}
                      {atencion.origen === 'MIGRACION' ? (
                        <span className={estilos.etiqueta}>Migración</span>
                      ) : null}
                      {atencion.rectificada ? (
                        <span className={estilos.etiqueta}>Rectificada</span>
                      ) : null}
                      {atencion.rectifica_a_id !== null ? (
                        <span className={estilos.etiqueta}>
                          Rectifica a #{atencion.rectifica_a_id}
                        </span>
                      ) : null}
                    </div>

                    {atencion.motivo ? (
                      <p>
                        <strong>Motivo:</strong> {atencion.motivo}
                      </p>
                    ) : null}
                    {atencion.diagnostico ? (
                      <p>
                        <strong>Diagnóstico:</strong> {atencion.diagnostico}
                      </p>
                    ) : null}
                    {atencion.tratamiento ? (
                      <p>
                        <strong>Tratamiento:</strong> {atencion.tratamiento}
                      </p>
                    ) : null}
                    {atencion.observaciones ? (
                      <p>
                        <strong>Observaciones:</strong> {atencion.observaciones}
                      </p>
                    ) : null}

                    {puedeEscribir && !atencion.rectificada ? (
                      <div className={estilos.acciones}>
                        <Boton
                          onClick={() => void abrirRectificacion(atencion)}
                          variante="secundario"
                        >
                          Rectificar
                        </Boton>
                      </div>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <LibretaVacunas items={vacunas} />

          <SubidaPlacas
            empleados={empleados}
            pacienteId={paciente.id}
            puedeEscribir={puedeEscribir}
          />
        </>
      ) : null}
    </section>
  );
}
