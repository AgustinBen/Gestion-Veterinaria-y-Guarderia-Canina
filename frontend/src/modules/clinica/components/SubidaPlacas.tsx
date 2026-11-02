import { useEffect, useState, type ChangeEvent, type FormEvent } from 'react';

import { Alerta } from '../../../core/components/ui/Alerta';
import { Boton } from '../../../core/components/ui/Boton';
import { Campo } from '../../../core/components/ui/Campo';
import type { EmpleadoDetalle } from '../../padron/tipos';
import {
  crearEstudio,
  descargarAdjunto,
  eliminarAdjunto,
  listarEstudios,
  mensajeDeError,
  subirAdjunto,
} from '../api';
import { fechaLocal } from '../fechas';
import type {
  AdjuntoResumen,
  EstudioResumen,
  TipoEstudio,
} from '../tipos';
import estilos from '../clinica.module.css';

const TIPOS_ESTUDIO: { value: TipoEstudio; label: string }[] = [
  { value: 'RADIOGRAFIA', label: 'Radiografía' },
  { value: 'ECOGRAFIA', label: 'Ecografía' },
  { value: 'ANALISIS', label: 'Análisis' },
  { value: 'OTRO', label: 'Otro' },
];

const ETIQUETA_ESTUDIO = Object.fromEntries(
  TIPOS_ESTUDIO.map((tipo) => [tipo.value, tipo.label]),
) as Record<TipoEstudio, string>;

type Props = {
  pacienteId: number;
  empleados: EmpleadoDetalle[];
  puedeEscribir: boolean;
};

export function SubidaPlacas({ pacienteId, empleados, puedeEscribir }: Props) {
  const veterinarios = empleados.filter(
    (empleado) => empleado.es_veterinario && empleado.activo,
  );
  const [estado, setEstado] = useState<'cargando' | 'listo' | 'error'>(
    'cargando',
  );
  const [intento, setIntento] = useState(0);
  const [estudios, setEstudios] = useState<EstudioResumen[]>([]);
  const [errorCarga, setErrorCarga] = useState('');
  const [tipo, setTipo] = useState<TipoEstudio>('RADIOGRAFIA');
  const [fecha, setFecha] = useState(fechaLocal(new Date()));
  const [descripcion, setDescripcion] = useState('');
  const [realizadoPor, setRealizadoPor] = useState(
    String(veterinarios[0]?.persona_id ?? ''),
  );
  const [errorFormulario, setErrorFormulario] = useState('');
  const [guardando, setGuardando] = useState(false);
  const [subiendo, setSubiendo] = useState<number | null>(null);
  const [progreso, setProgreso] = useState(0);
  const [errorArchivo, setErrorArchivo] = useState('');
  const [descargando, setDescargando] = useState<number | null>(null);
  const [confirmandoBaja, setConfirmandoBaja] = useState<number | null>(null);
  const [eliminando, setEliminando] = useState<number | null>(null);

  useEffect(() => {
    const controlador = new AbortController();
    let activo = true;

    async function cargar() {
      setEstado('cargando');
      setErrorCarga('');

      try {
        const datos = await listarEstudios(pacienteId, {
          signal: controlador.signal,
        });

        if (activo) {
          setEstudios(datos);
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
  }, [pacienteId, intento]);

  async function registrar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    setErrorFormulario('');

    if (descripcion.trim().length === 0) {
      setErrorFormulario('Contá qué estudio se realizó.');
      return;
    }

    if (realizadoPor === '') {
      setErrorFormulario('Elegí quién realizó el estudio.');
      return;
    }

    setGuardando(true);

    try {
      const creado = await crearEstudio(pacienteId, {
        tipo,
        fecha,
        descripcion: descripcion.trim(),
        realizado_por_empleado_id: Number(realizadoPor),
      });

      setEstudios((actuales) => [creado, ...actuales]);
      setDescripcion('');
      setTipo('RADIOGRAFIA');
      setFecha(fechaLocal(new Date()));
    } catch (fallo) {
      setErrorFormulario(mensajeDeError(fallo));
    } finally {
      setGuardando(false);
    }
  }

  async function subir(estudio: EstudioResumen, archivo: File) {
    setErrorArchivo('');
    setSubiendo(estudio.id);
    setProgreso(0);

    try {
      const adjunto = await subirAdjunto(estudio.id, archivo, {
        onProgreso: (fraccion) => setProgreso(fraccion),
      });

      setEstudios((actuales) =>
        actuales.map((item) =>
          item.id === estudio.id
            ? { ...item, adjuntos: [...item.adjuntos, adjunto] }
            : item,
        ),
      );
    } catch (fallo) {
      setErrorArchivo(mensajeDeError(fallo));
    } finally {
      setSubiendo(null);
      setProgreso(0);
    }
  }

  function elegirArchivo(
    estudio: EstudioResumen,
    evento: ChangeEvent<HTMLInputElement>,
  ) {
    const archivo = evento.target.files?.[0];
    evento.target.value = '';

    if (archivo) {
      void subir(estudio, archivo);
    }
  }

  async function descargar(adjunto: AdjuntoResumen) {
    setErrorArchivo('');
    setDescargando(adjunto.id);

    try {
      const blob = await descargarAdjunto(adjunto.id);
      const url = URL.createObjectURL(blob);
      const enlace = document.createElement('a');
      enlace.href = url;
      enlace.download = adjunto.nombre_original;
      document.body.append(enlace);
      enlace.click();
      enlace.remove();
      URL.revokeObjectURL(url);
    } catch (fallo) {
      setErrorArchivo(mensajeDeError(fallo));
    } finally {
      setDescargando(null);
    }
  }

  async function eliminar(estudio: EstudioResumen, adjunto: AdjuntoResumen) {
    setErrorArchivo('');
    setEliminando(adjunto.id);

    try {
      await eliminarAdjunto(adjunto.id);
      setEstudios((actuales) =>
        actuales.map((item) =>
          item.id === estudio.id
            ? {
                ...item,
                adjuntos: item.adjuntos.filter(
                  (existente) => existente.id !== adjunto.id,
                ),
              }
            : item,
        ),
      );
      setConfirmandoBaja(null);
    } catch (fallo) {
      setErrorArchivo(mensajeDeError(fallo));
    } finally {
      setEliminando(null);
    }
  }

  return (
    <section className={estilos.panel} aria-labelledby="estudios-titulo">
      <div className={estilos.panelCabecera}>
        <h3 className={estilos.panelTitulo} id="estudios-titulo">
          Estudios y placas
        </h3>
        <span className={estilos.etiqueta}>
          Imágenes y PDF · hasta 10 MB
        </span>
      </div>

      {errorArchivo ? (
        <Alerta role="alert" tono="error">
          {errorArchivo}
        </Alerta>
      ) : null}

      {puedeEscribir ? (
        <form className={estilos.formulario} onSubmit={(evento) => void registrar(evento)}>
          <div className={estilos.campos}>
            <Campo id="estudio-tipo" etiqueta="Tipo de estudio">
              <select
                id="estudio-tipo"
                onChange={(evento) => setTipo(evento.target.value as TipoEstudio)}
                value={tipo}
              >
                {TIPOS_ESTUDIO.map((opcion) => (
                  <option key={opcion.value} value={opcion.value}>
                    {opcion.label}
                  </option>
                ))}
              </select>
            </Campo>

            <Campo id="estudio-fecha" etiqueta="Fecha del estudio">
              <input
                id="estudio-fecha"
                onChange={(evento) => setFecha(evento.target.value)}
                type="date"
                value={fecha}
              />
            </Campo>

            <Campo id="estudio-descripcion" etiqueta="Descripción">
              <input
                id="estudio-descripcion"
                onChange={(evento) => setDescripcion(evento.target.value)}
                type="text"
                value={descripcion}
              />
            </Campo>

            <Campo id="estudio-realizado-por" etiqueta="Realizado por">
              <select
                id="estudio-realizado-por"
                onChange={(evento) => setRealizadoPor(evento.target.value)}
                value={realizadoPor}
              >
                <option value="">Elegí un veterinario</option>
                {veterinarios.map((empleado) => (
                  <option key={empleado.persona_id} value={empleado.persona_id}>
                    {empleado.nombre} {empleado.apellido}
                  </option>
                ))}
              </select>
            </Campo>
          </div>

          {errorFormulario ? (
            <Alerta role="alert" tono="error">
              {errorFormulario}
            </Alerta>
          ) : null}

          <div className={estilos.pieFormulario}>
            <Boton cargando={guardando} type="submit">
              Registrar estudio
            </Boton>
          </div>
        </form>
      ) : null}

      {estado === 'cargando' ? (
        <p className={estilos.cargando}>Cargando estudios…</p>
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
      ) : estudios.length === 0 ? (
        <p className={estilos.vacio}>Todavía no hay estudios cargados.</p>
      ) : (
        <ul className={estilos.estudios}>
          {estudios.map((estudio) => (
            <li className={estilos.estudio} key={estudio.id}>
              <div className={estilos.tarjetaCabecera}>
                <strong>{ETIQUETA_ESTUDIO[estudio.tipo]}</strong>
                <span className={estilos.etiqueta}>{estudio.fecha}</span>
              </div>
              <p>{estudio.descripcion}</p>

              {estudio.adjuntos.length === 0 ? (
                <p className={estilos.progreso}>Sin archivos adjuntos.</p>
              ) : (
                <ul className={estilos.adjuntos}>
                  {estudio.adjuntos.map((adjunto) => (
                    <li className={estilos.adjunto} key={adjunto.id}>
                      <span className={estilos.adjuntoNombre}>
                        {adjunto.nombre_original}
                      </span>
                      <Boton
                        cargando={descargando === adjunto.id}
                        onClick={() => void descargar(adjunto)}
                        type="button"
                        variante="texto"
                      >
                        Descargar
                      </Boton>
                      {puedeEscribir ? (
                        confirmandoBaja === adjunto.id ? (
                          <span role="group" aria-label="Confirmar eliminación">
                            <Boton
                              cargando={eliminando === adjunto.id}
                              onClick={() => void eliminar(estudio, adjunto)}
                              type="button"
                              variante="texto"
                            >
                              Confirmar eliminación
                            </Boton>
                            <Boton
                              disabled={eliminando === adjunto.id}
                              onClick={() => setConfirmandoBaja(null)}
                              type="button"
                              variante="texto"
                            >
                              Cancelar
                            </Boton>
                          </span>
                        ) : (
                          <Boton
                            aria-label={`Eliminar ${adjunto.nombre_original}`}
                            onClick={() => setConfirmandoBaja(adjunto.id)}
                            type="button"
                            variante="texto"
                          >
                            Eliminar
                          </Boton>
                        )
                      ) : null}
                    </li>
                  ))}
                </ul>
              )}

              {puedeEscribir ? (
                <label className={estilos.archivo}>
                  <span>Adjuntar imagen o PDF</span>
                  <input
                    accept="image/jpeg,image/png,image/webp,application/pdf"
                    aria-label={`Adjuntar archivo al estudio ${estudio.id}`}
                    disabled={subiendo !== null}
                    onChange={(evento) => elegirArchivo(estudio, evento)}
                    type="file"
                  />
                </label>
              ) : null}

              {subiendo === estudio.id ? (
                <p className={estilos.progreso} role="status">
                  Subiendo… {Math.round(progreso * 100)}%
                </p>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
