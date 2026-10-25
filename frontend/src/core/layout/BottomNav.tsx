import { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';

import type { Seccion } from '../auth/permisos';
import estilos from './BottomNav.module.css';

const MAX_PRINCIPALES = 4;

type Props = {
  secciones: readonly Seccion[];
};

export function BottomNav({ secciones }: Props) {
  const [abierto, setAbierto] = useState(false);
  const ubicacion = useLocation();
  const principales = secciones.slice(0, MAX_PRINCIPALES);
  const secundarias = secciones.slice(MAX_PRINCIPALES);
  const enSecundaria = secundarias.some((seccion) => seccion.ruta === ubicacion.pathname);

  return (
    <nav className={estilos.barra} aria-label="Navegación inferior">
      <div className={estilos.masPanel} id="mas-secciones" hidden={!abierto}>
        <p className={estilos.masTitulo}>Más secciones</p>
        {secundarias.map((seccion) => (
          <NavLink
            className={({ isActive }) =>
              [estilos.masEnlace, isActive ? estilos.activo : null].filter(Boolean).join(' ')
            }
            key={seccion.id}
            onClick={() => setAbierto(false)}
            to={seccion.ruta}
          >
            {seccion.etiqueta}
          </NavLink>
        ))}
      </div>

      <ul className={estilos.lista}>
        {principales.map((seccion) => (
          <li key={seccion.id}>
            <NavLink
              className={({ isActive }) =>
                [estilos.item, isActive ? estilos.activo : null].filter(Boolean).join(' ')
              }
              to={seccion.ruta}
            >
              <span className={estilos.etiqueta}>{seccion.etiquetaCorta}</span>
            </NavLink>
          </li>
        ))}

        {secundarias.length > 0 ? (
          <li>
            <button
              aria-controls="mas-secciones"
              aria-expanded={abierto}
              className={[estilos.item, enSecundaria ? estilos.activo : null]
                .filter(Boolean)
                .join(' ')}
              type="button"
              onClick={() => setAbierto((valor) => !valor)}
            >
              <span className={estilos.etiqueta}>Más</span>
            </button>
          </li>
        ) : null}
      </ul>
    </nav>
  );
}
