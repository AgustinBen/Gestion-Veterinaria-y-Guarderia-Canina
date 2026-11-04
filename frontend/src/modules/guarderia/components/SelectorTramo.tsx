import { Boton } from '../../../core/components/ui/Boton';
import { EtiquetaCampo } from '../../../core/components/ui/EtiquetaCampo';
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
        <EtiquetaCampo
          className={estilos.campo}
          etiqueta="Fecha de inicio"
          htmlFor="desde-fecha"
          obligatorio
        >
          <input
            id="desde-fecha"
            onChange={(evento) =>
              onChange({ ...tramo, desdeFecha: evento.currentTarget.value })
            }
            required
            type="date"
            value={tramo.desdeFecha}
          />
        </EtiquetaCampo>
        <EtiquetaCampo
          className={estilos.campo}
          etiqueta="Franja de inicio"
          htmlFor="desde-franja"
          obligatorio
        >
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
        </EtiquetaCampo>
        <EtiquetaCampo
          className={estilos.campo}
          etiqueta="Fecha de fin"
          htmlFor="hasta-fecha"
          obligatorio
        >
          <input
            id="hasta-fecha"
            onChange={(evento) =>
              onChange({ ...tramo, hastaFecha: evento.currentTarget.value })
            }
            required
            type="date"
            value={tramo.hastaFecha}
          />
        </EtiquetaCampo>
        <EtiquetaCampo
          className={estilos.campo}
          etiqueta="Franja de fin"
          htmlFor="hasta-franja"
          obligatorio
        >
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
        </EtiquetaCampo>
      </div>
    </fieldset>
  );
}
