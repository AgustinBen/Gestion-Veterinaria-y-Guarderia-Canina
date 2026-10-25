import { Link, Navigate, Outlet, useLocation } from 'react-router-dom';

import { useAuth } from '../auth/contexto';
import { rutaInicial, seccionDeRuta, seccionesVisibles } from '../auth/permisos';
import { BottomNav } from './BottomNav';
import { Sidebar } from './Sidebar';
import estilos from './AppLayout.module.css';

function formatearFechaHoy(fecha: Date): string {
  return new Intl.DateTimeFormat('es-AR', {
    day: 'numeric',
    month: 'short',
  }).format(fecha);
}

function fechaIsoLocal(fecha: Date): string {
  const mes = String(fecha.getMonth() + 1).padStart(2, '0');
  const dia = String(fecha.getDate()).padStart(2, '0');

  return `${fecha.getFullYear()}-${mes}-${dia}`;
}

export function AppLayout() {
  const { sesion, cerrarSesion } = useAuth();
  const ubicacion = useLocation();

  if (!sesion) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ desde: `${ubicacion.pathname}${ubicacion.search}` }}
      />
    );
  }

  const secciones = seccionesVisibles(sesion.rol);
  const inicio = rutaInicial(sesion.rol);
  const seccionActual = seccionDeRuta(ubicacion.pathname);
  const hoy = new Date();

  return (
    <>
      <a className={estilos.salto} href="#contenido-principal">
        Saltar al contenido
      </a>

      <div className={estilos.layout}>
        <Sidebar
          sesion={sesion}
          secciones={secciones}
          inicio={inicio}
          onSalir={cerrarSesion}
        />

        <div className={estilos.columna}>
          <header className={estilos.encabezado}>
            <div className={estilos.encabezadoTexto}>
              <nav className={estilos.migaja} aria-label="Ubicación">
                <Link
                  className={estilos.migajaMarca}
                  to={inicio}
                  aria-label="Huellitas, ir al inicio"
                >
                  Huellitas
                </Link>
                <span className={estilos.migajaSeparador} aria-hidden="true">
                  ›
                </span>
                <span className={estilos.migajaActual} aria-current="page">
                  {seccionActual?.etiqueta ?? 'Inicio'}
                </span>
              </nav>

            </div>

            <time className={estilos.fecha} dateTime={fechaIsoLocal(hoy)}>
              {formatearFechaHoy(hoy)}
            </time>

            <button
              aria-label="Cerrar sesión"
              className={estilos.botonSalirMovil}
              onClick={cerrarSesion}
              title="Cerrar sesión"
              type="button"
            >
              <svg
                aria-hidden="true"
                fill="none"
                focusable="false"
                stroke="currentColor"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                viewBox="0 0 24 24"
              >
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                <path d="m16 17 5-5-5-5" />
                <path d="M21 12H9" />
              </svg>
            </button>
          </header>

          <main className={estilos.contenido} id="contenido-principal" tabIndex={-1}>
            <Outlet />
          </main>
        </div>

        <BottomNav secciones={secciones} />
      </div>
    </>
  );
}
