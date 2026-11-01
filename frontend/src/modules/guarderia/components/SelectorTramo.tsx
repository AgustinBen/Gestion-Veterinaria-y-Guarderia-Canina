import { Boton } from '../../../core/components/ui/Boton';
import type { Franja } from '../tipos';
import estilos from '../guarderia.module.css';

export type Tramo = {
  desdeFecha: string;
  desdeFranja: Franja;
  hastaFecha: string;
  hastaFranja: Franja;
};

type Props = {
  tramo: Tramo;
  bloqueado?: boolean;
  onChange: (tramo: Tramo) => void;
};

export function SelectorTramo({ tramo, bloqueado = false, onChange }: Props) {
  function aplicarAtajo(desdeFranja: Franja, hastaFranja: Franja) {
    onChange({
      desdeFecha: tramo.desdeFecha,
      desdeFranja,
      hastaFecha: tramo.desdeFecha,
      hastaFranja,
    });
  }

  return (
    <fieldset className={estilos.grupoFormulario} disabled={bloqueado}>
      <legend>Tramo de estadía</legend>
      <div className={estilos.atajos}>
        <Boton onClick={() => aplicarAtajo('DIA', 'DIA')} variante="secundario">
          Solo día
        </Boton>
        <Boton onClick={() => aplicarAtajo('NOCHE', 'NOCHE')} variante="secundario">
          Solo noche
        </Boton>
        <Boton onClick={() => aplicarAtajo('DIA', 'NOCHE')} variante="secundario">
          24 horas
        </Boton>
      </div>
      <div className={estilos.grillaFormulario}>
        <label className={estilos.campo} htmlFor="desde-fecha">
          Fecha de inicio
          <input
            id="desde-fecha"
            onChange={(evento) =>
              onChange({ ...tramo, desdeFecha: evento.currentTarget.value })
            }
            required
            type="date"
            value={tramo.desdeFecha}
          />
        </label>
        <label className={estilos.campo} htmlFor="desde-franja">
          Franja de inicio
          <select
            id="desde-franja"
            onChange={(evento) =>
              onChange({
                ...tramo,
                desdeFranja:
                  evento.currentTarget.value === 'NOCHE' ? 'NOCHE' : 'DIA',
              })
            }
            value={tramo.desdeFranja}
          >
            <option value="DIA">Día</option>
            <option value="NOCHE">Noche</option>
          </select>
        </label>
        <label className={estilos.campo} htmlFor="hasta-fecha">
          Fecha de fin
          <input
            id="hasta-fecha"
            onChange={(evento) =>
              onChange({ ...tramo, hastaFecha: evento.currentTarget.value })
            }
            required
            type="date"
            value={tramo.hastaFecha}
          />
        </label>
        <label className={estilos.campo} htmlFor="hasta-franja">
          Franja de fin
          <select
            id="hasta-franja"
            onChange={(evento) =>
              onChange({
                ...tramo,
                hastaFranja:
                  evento.currentTarget.value === 'NOCHE' ? 'NOCHE' : 'DIA',
              })
            }
            value={tramo.hastaFranja}
          >
            <option value="DIA">Día</option>
            <option value="NOCHE">Noche</option>
          </select>
        </label>
      </div>
    </fieldset>
  );
}
