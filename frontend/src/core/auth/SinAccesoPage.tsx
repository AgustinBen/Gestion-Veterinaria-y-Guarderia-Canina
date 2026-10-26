import { Link } from 'react-router-dom';

import { useAuth } from './contexto';
import { rutaInicial } from './permisos';
import estilos from './SinAccesoPage.module.css';

export function SinAccesoPage() {
  const { sesion } = useAuth();
  const destino = sesion ? rutaInicial(sesion.rol) : '/login';

  return (
    <main className={estilos.pagina}>
      <section className={estilos.tarjeta} aria-labelledby="sin-acceso-titulo">
        <p className={estilos.antetitulo}>Acceso restringido</p>
        <h1 id="sin-acceso-titulo">Sin acceso</h1>
        <p className={estilos.texto}>
          Tu rol no tiene permiso para esta sección. Si necesitás entrar, pedile al Dueño que
          revise tus permisos.
        </p>
        <Link className={estilos.enlace} to={destino}>
          Volver al inicio
        </Link>
      </section>
    </main>
  );
}
