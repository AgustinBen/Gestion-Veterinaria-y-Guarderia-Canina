import { useRef, useState, type FormEvent } from 'react';

import { Alerta } from '../../../core/components/ui/Alerta';
import { Boton } from '../../../core/components/ui/Boton';
import { Campo } from '../../../core/components/ui/Campo';
import { DialogoConfirmacion } from '../../../core/components/ui/DialogoConfirmacion';
import { formatearDinero, parsearDinero } from '../../../core/formatos/dinero';
import { obtenerTitulares } from '../../padron/api';
import type { EmpleadoDetalle, PacienteResumen } from '../../padron/tipos';
import { crearTurno, mensajeDeError } from '../api';
import { aDatetimeLocal } from '../fechas';
import type { TipoTurnoMedico, Turno } from '../tipos';
import estilos from '../clinica.module.css';

const TIPOS: { value: TipoTurnoMedico; label: string }[] = [
  { value: 'CONSULTA', label: 'Consulta' },
  { value: 'VACUNA', label: 'Vacuna' },
  { value: 'CIRUGIA', label: 'Cirugía' },
  { value: 'ESTUDIO', label: 'Estudio' },
  { value: 'CONTROL', label: 'Control' },
];

type Props = {
  pacientes: PacienteResumen[];
  empleados: EmpleadoDetalle[];
  fechaInicial: string;
  onCreado: (turno: Turno) => void;
  onCancelar?: () => void;
};

export function NuevoTurno({
  pacientes,
  empleados,
  fechaInicial,
  onCreado,
  onCancelar,
}: Props) {
  const veterinarios = empleados.filter(
    (empleado) =>
      empleado.es_veterinario &&
      empleado.tipo === 'INTERNO' &&
      empleado.activo,
  );
  const externos = empleados.filter(
    (empleado) => empleado.tipo === 'EXTERNO' && empleado.activo,
  );
  const [pacienteId, setPacienteId] = useState('');
  const [tipo, setTipo] = useState<TipoTurnoMedico>('CONSULTA');
  const [veterinarioId, setVeterinarioId] = useState(
    String(veterinarios[0]?.persona_id ?? ''),
  );
  const [fecha, setFecha] = useState(fechaInicial);
  const [horaInicio, setHoraInicio] = useState('');
  const [horaFin, setHoraFin] = useState('');
  const [motivo, setMotivo] = useState('');
  const [externoId, setExternoId] = useState('');
  const [monto, setMonto] = useState('');
  const [error, setError] = useState('');
  const [guardando, setGuardando] = useState(false);
  const [aviso, setAviso] = useState<{ duenio: string; centavos: number } | null>(
    null,
  );
  const [consultandoDuenio, setConsultandoDuenio] = useState(false);
  const envioEnCurso = useRef(false);

  function cambiarTipo(nuevo: TipoTurnoMedico) {
    setTipo(nuevo);

    // La cirugía siempre la hace un veterinario externo: si hay uno solo, se
    // elige solo. Con varios se deja elegir para no asignar a uno por error.
    if (nuevo === 'CIRUGIA' && externoId === '' && externos.length === 1) {
      setExternoId(String(externos[0]?.persona_id ?? ''));
    }
  }

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    setError('');

    if (pacienteId === '') {
      setError('Elegí la mascota del turno.');
      return;
    }

    if (veterinarioId === '') {
      setError('Elegí el veterinario que atenderá el turno.');
      return;
    }

    if (fecha === '' || horaInicio === '' || horaFin === '') {
      setError('Completá la fecha y el horario del turno.');
      return;
    }

    if (horaFin <= horaInicio) {
      setError('El fin del turno debe ser posterior al inicio.');
      return;
    }

    if (tipo === 'CIRUGIA' && externoId === '') {
      setError('La cirugía requiere un veterinario externo.');
      return;
    }

    if (monto.trim() === '') {
      void agendar(undefined);
      return;
    }

    let centavos: number;

    try {
      centavos = parsearDinero(monto);
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'Monto inválido.');
      return;
    }

    // Antes de cargar el cobro se avisa a nombre de qué dueño quedará.
    setConsultandoDuenio(true);

    try {
      const titulares = await obtenerTitulares(Number(pacienteId));
      const principal = titulares.find((titular) => titular.principal);

      if (!principal) {
        setError('La mascota no tiene un dueño principal para cobrarle.');
        return;
      }

      setAviso({
        duenio: `${principal.nombre} ${principal.apellido}`.trim(),
        centavos,
      });
    } catch (fallo) {
      setError(mensajeDeError(fallo));
    } finally {
      setConsultandoDuenio(false);
    }
  }

  async function agendar(centavos: number | undefined) {
    if (envioEnCurso.current) {
      return;
    }

    envioEnCurso.current = true;
    setGuardando(true);
    setError('');

    try {
      const turno = await crearTurno({
        paciente_id: Number(pacienteId),
        tipo,
        veterinario_empleado_id: Number(veterinarioId),
        inicio: aDatetimeLocal(fecha, horaInicio),
        fin: aDatetimeLocal(fecha, horaFin),
        motivo: motivo.trim() || null,
        externo_empleado_id:
          tipo === 'CIRUGIA' ? Number(externoId) : undefined,
        ...(centavos !== undefined ? { monto_centavos: centavos } : {}),
      });

      setAviso(null);
      onCreado(turno);
    } catch (fallo) {
      setAviso(null);
      setError(mensajeDeError(fallo));
    } finally {
      envioEnCurso.current = false;
      setGuardando(false);
    }
  }

  return (
    <form className={`${estilos.panel} ${estilos.formulario}`} onSubmit={(evento) => void enviar(evento)}>
      <div className={estilos.panelCabecera}>
      </div>

      {error ? (
        <Alerta role="alert" tono="error">
          {error}
        </Alerta>
      ) : null}

      <div className={estilos.campos}>
        <Campo id="turno-paciente" etiqueta="Mascota">
          <select
            id="turno-paciente"
            onChange={(evento) => setPacienteId(evento.target.value)}
            value={pacienteId}
          >
            <option value="">Elegí una mascota</option>
            {pacientes.map((paciente) => (
              <option key={paciente.id} value={paciente.id}>
                {paciente.nombre} · {paciente.especie_nombre}
              </option>
            ))}
          </select>
        </Campo>

        <Campo id="turno-tipo" etiqueta="Tipo de turno">
          <select
            id="turno-tipo"
            onChange={(evento) =>
              cambiarTipo(evento.target.value as TipoTurnoMedico)
            }
            value={tipo}
          >
            {TIPOS.map((opcion) => (
              <option key={opcion.value} value={opcion.value}>
                {opcion.label}
              </option>
            ))}
          </select>
        </Campo>

        <Campo id="turno-veterinario" etiqueta="Veterinario">
          <select
            id="turno-veterinario"
            onChange={(evento) => setVeterinarioId(evento.target.value)}
            value={veterinarioId}
          >
            <option value="">Elegí un veterinario</option>
            {veterinarios.map((empleado) => (
              <option key={empleado.persona_id} value={empleado.persona_id}>
                {empleado.nombre} {empleado.apellido}
              </option>
            ))}
          </select>
        </Campo>

        {tipo === 'CIRUGIA' ? (
          <Campo id="turno-externo" etiqueta="Veterinario externo">
            <select
              id="turno-externo"
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

        <Campo id="turno-fecha" etiqueta="Fecha">
          <input
            id="turno-fecha"
            onChange={(evento) => setFecha(evento.target.value)}
            type="date"
            value={fecha}
          />
        </Campo>

        <Campo id="turno-inicio" etiqueta="Hora de inicio">
          <input
            id="turno-inicio"
            onChange={(evento) => setHoraInicio(evento.target.value)}
            type="time"
            value={horaInicio}
          />
        </Campo>

        <Campo id="turno-fin" etiqueta="Hora de fin">
          <input
            id="turno-fin"
            onChange={(evento) => setHoraFin(evento.target.value)}
            type="time"
            value={horaFin}
          />
        </Campo>

        <Campo
          ayuda="Se registra como cargo en Cobros, a nombre del dueño de la mascota."
          id="turno-monto"
          etiqueta="Monto a cobrar (opcional)"
        >
          <input
            id="turno-monto"
            inputMode="decimal"
            onChange={(evento) => setMonto(evento.target.value)}
            placeholder="Ej. 15.000 o 15.000,50"
            type="text"
            value={monto}
          />
        </Campo>

        <Campo id="turno-motivo" etiqueta="Motivo (opcional)">
          <textarea
            id="turno-motivo"
            onChange={(evento) => setMotivo(evento.target.value)}
            rows={2}
            value={motivo}
          />
        </Campo>
      </div>

      <div className={estilos.pieFormulario}>
        {onCancelar ? (
          <Boton onClick={onCancelar} type="button" variante="secundario">
            Cancelar
          </Boton>
        ) : null}
        <Boton cargando={guardando || consultandoDuenio} type="submit">
          Agendar turno
        </Boton>
      </div>

      <DialogoConfirmacion
        abierto={aviso !== null}
        bloquearCierre={guardando}
        onCerrar={() => setAviso(null)}
        pie={
          <>
            <Boton
              disabled={guardando}
              onClick={() => setAviso(null)}
              type="button"
              variante="secundario"
            >
              Volver
            </Boton>
            <Boton
              cargando={guardando}
              onClick={() => void agendar(aviso?.centavos)}
              type="button"
            >
              Confirmar y agendar
            </Boton>
          </>
        }
        titulo="Confirmar cobro del turno"
      >
        {aviso ? (
          <p>
            Se estará cargando este pago ({formatearDinero(aviso.centavos)})
            dentro de la cuenta de <strong>{aviso.duenio}</strong>.
          </p>
        ) : null}
      </DialogoConfirmacion>
    </form>
  );
}
