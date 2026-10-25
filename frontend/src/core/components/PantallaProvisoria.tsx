import type { SeccionId } from '../auth/permisos';
import { useAuth } from '../auth/contexto';
import { puedeAcceder } from '../auth/permisos';
import estilos from './PantallaProvisoria.module.css';

type Props = {
  seccion: SeccionId;
  titulo: string;
  descripcion: string;
};

export function PantallaProvisoria({ seccion, titulo, descripcion }: Props) {
  const { sesion } = useAuth();
  const soloLectura = sesion ? !puedeAcceder(sesion.rol, seccion, 'escritura') : false;

  return (
    <section className={estilos.pagina} aria-labelledby={`titulo-${seccion}`}>
      <p className={estilos.antetitulo}>Módulo</p>

      <div className={estilos.filaTitulo}>
        <h1 id={`titulo-${seccion}`}>{titulo}</h1>
        {soloLectura ? <span className={estilos.insignia}>Solo lectura</span> : null}
      </div>

      <p className={estilos.descripcion}>{descripcion}</p>

      <div className={estilos.panel}>
        <p className={estilos.panelTitulo}>Pantalla provisoria</p>
        <p className={estilos.panelTexto}>
          La base de navegación y sesión ya está lista. La pantalla real de este módulo se
          implementa en su ticket correspondiente.
        </p>
      </div>
    </section>
  );
}
