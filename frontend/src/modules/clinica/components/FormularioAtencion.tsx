import { useState, type FormEvent } from 'react';

import { Alerta } from '../../../core/components/ui/Alerta';
import { Boton } from '../../../core/components/ui/Boton';
import { Campo } from '../../../core/components/ui/Campo';
import type { EmpleadoDetalle } from '../../padron/tipos';
import { crearAtencion, mensajeDeError, rectificarAtencion } from '../api';
import { fechaLocal } from '../fechas';
import type {
  AtencionCrear,
  AtencionDetalle,
  TipoAtencion,
} from '../tipos';
import estilos from '../clinica.module.css';

const TIPOS: { value: TipoAtencion; label: string }[] = [
  { value: 'CONSULTA', label: 'Consulta' },
  { value: 'VACUNA', label: 'Vacuna' },
  { value: 'CIRUGIA', label: 'Cirugía' },
  { value: 'TRATAMIENTO', label: 'Tratamiento' },
  { value: 'ESTUDIO', label: 'Estudio' },
];

type Props = {
  pacienteId: number;
  empleados: EmpleadoDetalle[];
  atencion?: AtencionDetalle | null;
  onGuardado: (atencion: AtencionDetalle) => void;
  onCancelar?: () => void;
};

export function FormularioAtencion({
  pacienteId,
  empleados,
  atencion = null,
  onGuardado,
  onCancelar,
}: Props) {
  const veterinarios = empleados.filter(
    (empleado) => empleado.es_veterinario && empleado.activo,
  );
  const externos = empleados.filter(
    (empleado) => empleado.tipo === 'EXTERNO' && empleado.activo,
  );
  const [tipo, setTipo] = useState<TipoAtencion>(atencion?.tipo ?? 'CONSULTA');
  const [veterinarioId, setVeterinarioId] = useState(
    String(atencion?.veterinario_empleado_id ?? veterinarios[0]?.persona_id ?? ''),
  );
  const [motivo, setMotivo] = useState(atencion?.motivo ?? '');
  const [diagnostico, setDiagnostico] = useState(atencion?.diagnostico ?? '');
  const [tratamiento, setTratamiento] = useState(atencion?.tratamiento ?? '');
  const [observaciones, setObservaciones] = useState(
    atencion?.observaciones ?? '',
  );
  const [cirujanoId, setCirujanoId] = useState(
    String(atencion?.cirujano_externo_id ?? ''),
  );
  const [nombreVacuna, setNombreVacuna] = useState(
    atencion?.vacuna?.nombre_vacuna ?? '',
  );
  const [lote, setLote] = useState(atencion?.vacuna?.lote ?? '');
  const [fechaAplicacion, setFechaAplicacion] = useState(
    atencion?.vacuna?.fecha_aplicacion ?? fechaLocal(new Date()),
  );
  const [proximaDosis, setProximaDosis] = useState(
    atencion?.vacuna?.proxima_dosis ?? '',
  );
  const [error, setError] = useState('');
  const [guardando, setGuardando] = useState(false);

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    setError('');

    if (veterinarioId === '') {
      setError('Elegí el veterinario que realizó la atención.');
      return;
    }

    const datos: AtencionCrear = {
      tipo,
      veterinario_empleado_id: Number(veterinarioId),
      motivo: motivo.trim() || null,
      diagnostico: diagnostico.trim() || null,
      tratamiento: tratamiento.trim() || null,
      observaciones: observaciones.trim() || null,
    };

    if (tipo === 'CIRUGIA') {
      if (cirujanoId === '') {
        setError('La cirugía requiere un cirujano externo.');
        return;
      }

      datos.cirujano_externo_id = Number(cirujanoId);
    }

    if (tipo === 'VACUNA') {
      if (nombreVacuna.trim().length === 0) {
        setError('Indicá el nombre de la vacuna.');
        return;
      }

      if (fechaAplicacion === '') {
        setError('Indicá la fecha de aplicación.');
        return;
      }

      datos.vacuna = {
        nombre_vacuna: nombreVacuna.trim(),
        lote: lote.trim() || null,
        fecha_aplicacion: fechaAplicacion,
        proxima_dosis: proximaDosis || null,
      };
    }

    setGuardando(true);

    try {
      const guardada = atencion
        ? await rectificarAtencion(atencion.id, datos)
        : await crearAtencion(pacienteId, datos);
      onGuardado(guardada);
    } catch (fallo) {
      setError(mensajeDeError(fallo));
    } finally {
      setGuardando(false);
    }
  }

  return (
    <form className={estilos.formulario} onSubmit={(evento) => void enviar(evento)}>
      <div className={estilos.panelCabecera}>
        <h3 className={estilos.panelTitulo}>
          {atencion ? `Rectificar atención #${atencion.id}` : 'Nueva atención'}
        </h3>
        {atencion ? (
          <span className={estilos.etiqueta}>
            La original queda como rectificada
          </span>
        ) : null}
      </div>

      {error ? (
        <Alerta role="alert" tono="error">
          {error}
        </Alerta>
      ) : null}

      <div className={estilos.campos}>
        <Campo id="atencion-tipo" etiqueta="Tipo de atención">
          <select
            id="atencion-tipo"
            onChange={(evento) => setTipo(evento.target.value as TipoAtencion)}
            value={tipo}
          >
            {TIPOS.map((opcion) => (
              <option key={opcion.value} value={opcion.value}>
                {opcion.label}
              </option>
            ))}
          </select>
        </Campo>

        <Campo id="atencion-veterinario" etiqueta="Veterinario">
          <select
            id="atencion-veterinario"
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
          <Campo id="atencion-cirujano" etiqueta="Cirujano externo">
            <select
              id="atencion-cirujano"
              onChange={(evento) => setCirujanoId(evento.target.value)}
              value={cirujanoId}
            >
              <option value="">Elegí un cirujano externo</option>
              {externos.map((empleado) => (
                <option key={empleado.persona_id} value={empleado.persona_id}>
                  {empleado.nombre} {empleado.apellido}
                </option>
              ))}
            </select>
          </Campo>
        ) : null}

        {tipo === 'VACUNA' ? (
          <>
            <Campo id="atencion-vacuna" etiqueta="Nombre de la vacuna">
              <input
                id="atencion-vacuna"
                onChange={(evento) => setNombreVacuna(evento.target.value)}
                type="text"
                value={nombreVacuna}
              />
            </Campo>
            <Campo id="atencion-lote" etiqueta="Lote (opcional)">
              <input
                id="atencion-lote"
                onChange={(evento) => setLote(evento.target.value)}
                type="text"
                value={lote}
              />
            </Campo>
            <Campo id="atencion-fecha-vacuna" etiqueta="Fecha de aplicación">
              <input
                id="atencion-fecha-vacuna"
                onChange={(evento) => setFechaAplicacion(evento.target.value)}
                type="date"
                value={fechaAplicacion}
              />
            </Campo>
            <Campo id="atencion-proxima-dosis" etiqueta="Próxima dosis (opcional)">
              <input
                id="atencion-proxima-dosis"
                onChange={(evento) => setProximaDosis(evento.target.value)}
                type="date"
                value={proximaDosis}
              />
            </Campo>
          </>
        ) : null}

        <Campo id="atencion-motivo" etiqueta="Motivo">
          <textarea
            id="atencion-motivo"
            onChange={(evento) => setMotivo(evento.target.value)}
            rows={2}
            value={motivo}
          />
        </Campo>

        <Campo id="atencion-diagnostico" etiqueta="Diagnóstico">
          <textarea
            id="atencion-diagnostico"
            onChange={(evento) => setDiagnostico(evento.target.value)}
            rows={2}
            value={diagnostico}
          />
        </Campo>

        <Campo id="atencion-tratamiento" etiqueta="Tratamiento">
          <textarea
            id="atencion-tratamiento"
            onChange={(evento) => setTratamiento(evento.target.value)}
            rows={2}
            value={tratamiento}
          />
        </Campo>

        <Campo id="atencion-observaciones" etiqueta="Observaciones">
          <textarea
            id="atencion-observaciones"
            onChange={(evento) => setObservaciones(evento.target.value)}
            rows={2}
            value={observaciones}
          />
        </Campo>
      </div>

      <div className={estilos.pieFormulario}>
        {onCancelar ? (
          <Boton onClick={onCancelar} type="button" variante="secundario">
            Cancelar
          </Boton>
        ) : null}
        <Boton cargando={guardando} type="submit">
          {atencion ? 'Guardar rectificación' : 'Guardar atención'}
        </Boton>
      </div>
    </form>
  );
}
