import { useEffect, useState, type FormEvent } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { useAuth } from '../../../core/auth/contexto';
import { Alerta } from '../../../core/components/ui/Alerta';
import { Boton } from '../../../core/components/ui/Boton';
import { Campo } from '../../../core/components/ui/Campo';
import { DialogoConfirmacion } from '../../../core/components/ui/DialogoConfirmacion';
import { listarEmpleados, obtenerPaciente } from '../../padron/api';
import type { EmpleadoDetalle, PacienteDetalle } from '../../padron/tipos';
import {
  cancelarTurno,
  listarAtenciones,
  marcarTurnoAtendido,
  marcarTurnoAusente,
  mensajeDeError,
  obtenerTurno,
  reprogramarTurno,
} from '../api';
import { FlujoExterno } from '../components/FlujoExterno';
import {
  aDatetimeLocal,
  fechaDeIso,
  formatearFechaLarga,
  horaDeIso,
} from '../fechas';
import {
  puedeCrearTurnos,
  puedeEscribirHistoria,
  puedeVerCostoExterno,
} from '../permisos';
import type {
  AtencionResumen,
  EstadoTurno,
  TipoTurnoMedico,
  Turno,
} from '../tipos';
import estilos from '../clinica.module.css';

const ETIQUETA_TURNO: Record<TipoTurnoMedico, string> = {
  CONSULTA: 'Consulta',
  VACUNA: 'Vacuna',
  CIRUGIA: 'Cirugía',
  ESTUDIO: 'Estudio',
  CONTROL: 'Control',
};

const ETIQUETA_ESTADO: Record<EstadoTurno, string> = {
  PROGRAMADO: 'Programado',
  PENDIENTE_EXTERNO: 'Pendiente externo',
  CONFIRMADO: 'Confirmado',
  ATENDIDO: 'Atendido',
  CANCELADO: 'Cancelado',
  AUSENTE: 'Ausente',
};

const CLASE_ESTADO: Record<EstadoTurno, string> = {
  PROGRAMADO: estilos.estadoProgramado ?? '',
  PENDIENTE_EXTERNO: estilos.estadoPendiente ?? '',
  CONFIRMADO: estilos.estadoConfirmado ?? '',
  ATENDIDO: estilos.estadoAtendido ?? '',
  CANCELADO: estilos.estadoCancelado ?? '',
  AUSENTE: estilos.estadoAusente ?? '',
};

type Estado = 'cargando' | 'listo' | 'error';
type Dialogo = 'cancelar' | 'atender' | 'reprogramar' | 'ausente' | null;

export function DetalleTurno() {
  const { turnoId } = useParams();
  const id = Number(turnoId);
  const navegar = useNavigate();
  const { sesion } = useAuth();
  const [turno, setTurno] = useState<Turno | null>(null);
  const [paciente, setPaciente] = useState<PacienteDetalle | null>(null);
  const [empleados, setEmpleados] = useState<EmpleadoDetalle[]>([]);
  const [atencionesCirugia, setAtencionesCirugia] = useState<AtencionResumen[]>(
    [],
  );
  const [estado, setEstado] = useState<Estado>('cargando');
  const [error, setError] = useState('');
  const [exito, setExito] = useState('');
  const [errorAccion, setErrorAccion] = useState('');
  const [intento, setIntento] = useState(0);
  const [dialogo, setDialogo] = useState<Dialogo>(null);
  const [motivoCancelacion, setMotivoCancelacion] = useState('');
  const [atencionId, setAtencionId] = useState('');
  const [reproFecha, setReproFecha] = useState('');
  const [reproInicio, setReproInicio] = useState('');
  const [reproFin, setReproFin] = useState('');
  const [reproVeterinario, setReproVeterinario] = useState('');
  const [procesando, setProcesando] = useState(false);

  useEffect(() => {
    const controlador = new AbortController();
    let activo = true;

    async function cargar() {
      if (!Number.isInteger(id) || id <= 0) {
        setError('El turno indicado no es válido.');
        setEstado('error');
        return;
      }

      setEstado('cargando');
      setError('');

      try {
        const datosTurno = await obtenerTurno(id, {
          signal: controlador.signal,
        });
        const esCirugia = datosTurno.tipo === 'CIRUGIA';
        const [datosPaciente, datosEmpleados, datosAtenciones] =
          await Promise.all([
            obtenerPaciente(datosTurno.paciente_id, {
              signal: controlador.signal,
            }),
            listarEmpleados({ signal: controlador.signal }),
            esCirugia
              ? listarAtenciones(datosTurno.paciente_id, {
                  tipo: 'CIRUGIA',
                  signal: controlador.signal,
                })
              : Promise.resolve([]),
          ]);

        if (activo) {
          setTurno(datosTurno);
          setPaciente(datosPaciente);
          setEmpleados(datosEmpleados);
          setAtencionesCirugia(datosAtenciones);
          setReproFecha(fechaDeIso(datosTurno.inicio));
          setReproInicio(horaDeIso(datosTurno.inicio));
          setReproFin(horaDeIso(datosTurno.fin));
          setReproVeterinario(String(datosTurno.veterinario_empleado_id));
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

  const veterinarios = empleados.filter(
    (empleado) => empleado.es_veterinario && empleado.activo,
  );

  function nombreEmpleado(empleadoId: number | null): string {
    if (empleadoId === null) {
      return 'sin asignar';
    }

    const encontrado = empleados.find(
      (empleado) => empleado.persona_id === empleadoId,
    );

    return encontrado
      ? `${encontrado.nombre} ${encontrado.apellido}`.trim()
      : `Empleado #${empleadoId}`;
  }

  async function cancelar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();

    if (motivoCancelacion.trim().length === 0) {
      setErrorAccion('Indicá el motivo de la cancelación.');
      return;
    }

    setProcesando(true);
    setErrorAccion('');

    try {
      const actualizado = await cancelarTurno(id, motivoCancelacion.trim());
      setTurno(actualizado);
      setDialogo(null);
      setMotivoCancelacion('');
      setExito('El turno quedó cancelado.');
    } catch (fallo) {
      setErrorAccion(mensajeDeError(fallo));
    } finally {
      setProcesando(false);
    }
  }

  async function marcarAusente() {
    setProcesando(true);
    setErrorAccion('');

    try {
      const actualizado = await marcarTurnoAusente(id);
      setTurno(actualizado);
      setDialogo(null);
      setExito('El turno quedó marcado como ausente.');
    } catch (fallo) {
      setErrorAccion(mensajeDeError(fallo));
    } finally {
      setProcesando(false);
    }
  }

  async function marcarAtendido(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();

    if (turno?.tipo === 'CIRUGIA' && atencionId === '') {
      setErrorAccion('Elegí la atención de cirugía que corresponde al turno.');
      return;
    }

    setProcesando(true);
    setErrorAccion('');

    try {
      const actualizado = await marcarTurnoAtendido(
        id,
        atencionId === '' ? undefined : Number(atencionId),
      );
      setTurno(actualizado);
      setDialogo(null);
      setAtencionId('');
      setExito(
        actualizado.gasto_registrado
          ? 'Turno atendido. Se registró el gasto del veterinario externo.'
          : 'Turno atendido.',
      );
    } catch (fallo) {
      setErrorAccion(mensajeDeError(fallo));
    } finally {
      setProcesando(false);
    }
  }

  async function reprogramar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();

    if (
      reproFecha === '' ||
      reproInicio === '' ||
      reproFin === '' ||
      reproVeterinario === ''
    ) {
      setErrorAccion('Completá la fecha, el horario y el veterinario.');
      return;
    }

    if (reproFin <= reproInicio) {
      setErrorAccion('El fin del turno debe ser posterior al inicio.');
      return;
    }

    setProcesando(true);
    setErrorAccion('');

    try {
      const actualizado = await reprogramarTurno(id, {
        inicio: aDatetimeLocal(reproFecha, reproInicio),
        fin: aDatetimeLocal(reproFecha, reproFin),
        veterinario_empleado_id: Number(reproVeterinario),
      });
      setTurno(actualizado);
      setDialogo(null);
      setExito('El turno quedó reprogramado.');
    } catch (fallo) {
      setErrorAccion(mensajeDeError(fallo));
    } finally {
      setProcesando(false);
    }
  }

  async function manejarEvento() {
    setExito('El evento del veterinario externo quedó registrado.');

    try {
      const actualizado = await obtenerTurno(id);
      setTurno(actualizado);
    } catch {
      // El evento ya se registró; si falla la relectura se mantiene la vista.
    }
  }

  const puedeOperar =
    turno?.estado === 'PROGRAMADO' || turno?.estado === 'CONFIRMADO';
  // Atiende quien escribe la historia clínica (Dueño y Veterinario); gestiona
  // la agenda quien agenda (Dueño y Personal).
  const puedeAtender = puedeEscribirHistoria(sesion?.rol ?? null);
  const puedeGestionar = puedeCrearTurnos(sesion?.rol ?? null);

  return (
    <section className={estilos.pagina} aria-labelledby="titulo-turno">
      <header className={estilos.cabecera}>
        <div className={estilos.introduccion}>
          <p className={estilos.antetitulo}>Agenda veterinaria</p>
          <h1 className={estilos.titulo} id="titulo-turno">
            Turno {turno ? `#${turno.id}` : ''}
          </h1>
          <p className={estilos.subtitulo}>
            Estado y registro del veterinario externo.
          </p>
        </div>
        <Link className={estilos.enlace} to="/turnos">
          Volver a la agenda
        </Link>
      </header>

      {estado === 'cargando' ? (
        <section className={estilos.panel}>
          <p className={estilos.cargando}>Cargando turno…</p>
        </section>
      ) : estado === 'error' ? (
        <section className={estilos.panel}>
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
            {error}
          </Alerta>
        </section>
      ) : turno ? (
        <>
          {exito ? (
            <Alerta role="status" tono="exito">
              {exito}
            </Alerta>
          ) : null}

          {errorAccion ? (
            <Alerta role="alert" tono="error">
              {errorAccion}
            </Alerta>
          ) : null}

          <section className={estilos.panel} aria-labelledby="datos-turno">
            <div className={estilos.panelCabecera}>
              <h2 className={estilos.panelTitulo} id="datos-turno">
                {paciente?.nombre ?? `Mascota #${turno.paciente_id}`}
              </h2>
              <span
                className={`${estilos.estado} ${CLASE_ESTADO[turno.estado]}`.trim()}
              >
                {ETIQUETA_ESTADO[turno.estado]}
              </span>
            </div>

            <div className={estilos.meta}>
              <span>
                <strong>{formatearFechaLarga(fechaDeIso(turno.inicio))}</strong>
              </span>
              <span>
                De <strong>{horaDeIso(turno.inicio)}</strong> a{' '}
                <strong>{horaDeIso(turno.fin)}</strong>
              </span>
              <span>Tipo: {ETIQUETA_TURNO[turno.tipo]}</span>
              <span>
                Veterinario:{' '}
                <strong>{nombreEmpleado(turno.veterinario_empleado_id)}</strong>
              </span>
              <span>
                Externo actual: <strong>{nombreEmpleado(turno.externo_actual_id)}</strong>
              </span>
              {paciente ? (
                <span>
                  {paciente.especie_nombre}
                  {paciente.raza_nombre ? ` · ${paciente.raza_nombre}` : ''}
                </span>
              ) : null}
            </div>

            {turno.motivo ? <p>Motivo: {turno.motivo}</p> : null}

            <div className={estilos.acciones}>
              {puedeOperar ? (
                <>
                  {puedeAtender ? (
                    <Boton onClick={() => setDialogo('atender')} type="button">
                      Marcar atendido
                    </Boton>
                  ) : null}
                  {puedeGestionar ? (
                    <Boton
                      onClick={() => setDialogo('reprogramar')}
                      type="button"
                      variante="secundario"
                    >
                      Reprogramar
                    </Boton>
                  ) : null}
                </>
              ) : null}

              {turno.estado !== 'CANCELADO' &&
              turno.estado !== 'ATENDIDO' &&
              turno.estado !== 'AUSENTE' ? (
                <>
                  {puedeOperar ? (
                    <Boton
                      onClick={() => setDialogo('ausente')}
                      type="button"
                      variante="secundario"
                    >
                      Marcar ausente
                    </Boton>
                  ) : null}
                  {puedeGestionar ? (
                    <Boton
                      onClick={() => setDialogo('cancelar')}
                      type="button"
                      variante="peligro"
                    >
                      Cancelar turno
                    </Boton>
                  ) : null}
                </>
              ) : null}

              <Boton
                onClick={() => navegar('/turnos')}
                type="button"
                variante="texto"
              >
                Volver
              </Boton>
            </div>
          </section>

          {turno.tipo === 'CIRUGIA' ? (
            <FlujoExterno
              empleados={empleados}
              onEvento={() => void manejarEvento()}
              puedeConfirmarCosto={puedeVerCostoExterno(sesion?.rol ?? null)}
              turnoId={turno.id}
            />
          ) : null}

          <DialogoConfirmacion
            abierto={dialogo === 'cancelar'}
            onCerrar={() => setDialogo(null)}
            pie={
              <>
                <Boton
                  onClick={() => setDialogo(null)}
                  type="button"
                  variante="secundario"
                >
                  Volver
                </Boton>
                <Boton
                  cargando={procesando}
                  form="form-cancelar-turno"
                  type="submit"
                  variante="peligro"
                >
                  Cancelar turno
                </Boton>
              </>
            }
            titulo="Cancelar turno"
          >
            <form
              className={estilos.formulario}
              id="form-cancelar-turno"
              onSubmit={(evento) => void cancelar(evento)}
            >
              <p>El turno quedará registrado como cancelado.</p>
              <Campo id="cancelar-motivo" etiqueta="Motivo">
                <textarea
                  id="cancelar-motivo"
                  onChange={(evento) => setMotivoCancelacion(evento.target.value)}
                  rows={3}
                  value={motivoCancelacion}
                />
              </Campo>
            </form>
          </DialogoConfirmacion>

          <DialogoConfirmacion
            abierto={dialogo === 'ausente'}
            bloquearCierre={procesando}
            descripcion="El turno quedará registrado como ausente y ya no se podrá atender."
            onCerrar={() => setDialogo(null)}
            pie={
              <>
                <Boton
                  disabled={procesando}
                  onClick={() => setDialogo(null)}
                  type="button"
                  variante="secundario"
                >
                  Volver
                </Boton>
                <Boton
                  cargando={procesando}
                  onClick={() => void marcarAusente()}
                  type="button"
                  variante="peligro"
                >
                  Confirmar ausencia
                </Boton>
              </>
            }
            titulo="Marcar turno como ausente"
          >
            <p>¿Confirmás que la mascota no se presentó al turno?</p>
          </DialogoConfirmacion>

          <DialogoConfirmacion
            abierto={dialogo === 'atender'}
            onCerrar={() => setDialogo(null)}
            pie={
              <>
                <Boton
                  onClick={() => setDialogo(null)}
                  type="button"
                  variante="secundario"
                >
                  Volver
                </Boton>
                <Boton
                  cargando={procesando}
                  form="form-atender-turno"
                  type="submit"
                >
                  Marcar atendido
                </Boton>
              </>
            }
            titulo="Marcar turno atendido"
          >
            <form
              className={estilos.formulario}
              id="form-atender-turno"
              onSubmit={(evento) => void marcarAtendido(evento)}
            >
              {turno.tipo === 'CIRUGIA' ? (
                atencionesCirugia.length === 0 ? (
                  <Alerta tono="aviso">
                    Primero registrá la atención de cirugía en la historia
                    clínica.
                  </Alerta>
                ) : (
                  <Campo
                    ayuda="La cirugía debe coincidir con el veterinario externo del turno."
                    id="atender-atencion"
                    etiqueta="Atención de cirugía"
                  >
                    <select
                      id="atender-atencion"
                      onChange={(evento) => setAtencionId(evento.target.value)}
                      value={atencionId}
                    >
                      <option value="">Elegí una atención</option>
                      {atencionesCirugia.map((atencion) => (
                        <option key={atencion.id} value={atencion.id}>
                          #{atencion.id} · {formatearFechaLarga(fechaDeIso(atencion.fecha_hora))}
                        </option>
                      ))}
                    </select>
                  </Campo>
                )
              ) : (
                <p>El turno quedará registrado como atendido.</p>
              )}
            </form>
          </DialogoConfirmacion>

          <DialogoConfirmacion
            abierto={dialogo === 'reprogramar'}
            onCerrar={() => setDialogo(null)}
            pie={
              <>
                <Boton
                  onClick={() => setDialogo(null)}
                  type="button"
                  variante="secundario"
                >
                  Volver
                </Boton>
                <Boton
                  cargando={procesando}
                  form="form-reprogramar-turno"
                  type="submit"
                >
                  Guardar cambios
                </Boton>
              </>
            }
            titulo="Reprogramar turno"
          >
            <form
              className={estilos.formulario}
              id="form-reprogramar-turno"
              onSubmit={(evento) => void reprogramar(evento)}
            >
              <Campo id="reprogramar-fecha" etiqueta="Fecha">
                <input
                  id="reprogramar-fecha"
                  onChange={(evento) => setReproFecha(evento.target.value)}
                  type="date"
                  value={reproFecha}
                />
              </Campo>
              <Campo id="reprogramar-inicio" etiqueta="Hora de inicio">
                <input
                  id="reprogramar-inicio"
                  onChange={(evento) => setReproInicio(evento.target.value)}
                  type="time"
                  value={reproInicio}
                />
              </Campo>
              <Campo id="reprogramar-fin" etiqueta="Hora de fin">
                <input
                  id="reprogramar-fin"
                  onChange={(evento) => setReproFin(evento.target.value)}
                  type="time"
                  value={reproFin}
                />
              </Campo>
              <Campo id="reprogramar-veterinario" etiqueta="Veterinario">
                <select
                  id="reprogramar-veterinario"
                  onChange={(evento) => setReproVeterinario(evento.target.value)}
                  value={reproVeterinario}
                >
                  <option value="">Elegí un veterinario</option>
                  {veterinarios.map((empleado) => (
                    <option key={empleado.persona_id} value={empleado.persona_id}>
                      {empleado.nombre} {empleado.apellido}
                    </option>
                  ))}
                </select>
              </Campo>
            </form>
          </DialogoConfirmacion>
        </>
      ) : null}
    </section>
  );
}
