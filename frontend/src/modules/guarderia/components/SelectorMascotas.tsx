import type { PacienteResumen } from '../../padron/tipos';
import estilos from '../guarderia.module.css';

type Props = {
  mascotas: PacienteResumen[];
  seleccionadas: ReadonlySet<number>;
  cuidadosExtras: Readonly<Record<number, boolean>>;
  tiposCuidado: Readonly<Record<number, string>>;
  bloqueado?: boolean;
  onToggle: (pacienteId: number) => void;
  onCuidadoExtraChange: (pacienteId: number, activo: boolean) => void;
  onTipoCuidadoChange: (pacienteId: number, tipo: string) => void;
};

export function SelectorMascotas({
  mascotas,
  seleccionadas,
  cuidadosExtras,
  tiposCuidado,
  bloqueado = false,
  onToggle,
  onCuidadoExtraChange,
  onTipoCuidadoChange,
}: Props) {
  if (mascotas.length === 0) {
    return <p className={estilos.vacio}>Este tutor no tiene mascotas activas en el padrón.</p>;
  }

  return (
    <fieldset className={estilos.grupoFormulario} disabled={bloqueado}>
      <legend>Mascotas que se reservan</legend>
      <div className={estilos.listaMascotas}>
        {mascotas.map((mascota) => {
          const seleccionada = seleccionadas.has(mascota.id);

          return (
            <div className={estilos.mascota} key={mascota.id}>
              <label className={estilos.opcionMascota}>
                <input
                  checked={seleccionada}
                  onChange={() => onToggle(mascota.id)}
                  type="checkbox"
                />
                <span>
                  {mascota.nombre} · {mascota.especie_nombre}
                </span>
              </label>
              {seleccionada ? (
                <>
                  <label className={estilos.opcionCuidado}>
                    <input
                      checked={cuidadosExtras[mascota.id] ?? false}
                      onChange={(evento) =>
                        onCuidadoExtraChange(mascota.id, evento.currentTarget.checked)
                      }
                      type="checkbox"
                    />
                    Cuidados extras
                  </label>
                  {cuidadosExtras[mascota.id] ? (
                    <label className={estilos.campo} htmlFor={`tipo-cuidado-${mascota.id}`}>
                      Tipo de cuidado (opcional)
                      <textarea
                        id={`tipo-cuidado-${mascota.id}`}
                        onChange={(evento) =>
                          onTipoCuidadoChange(mascota.id, evento.currentTarget.value)
                        }
                        rows={2}
                        value={tiposCuidado[mascota.id] ?? ''}
                      />
                    </label>
                  ) : null}
                </>
              ) : null}
            </div>
          );
        })}
      </div>
    </fieldset>
  );
}
