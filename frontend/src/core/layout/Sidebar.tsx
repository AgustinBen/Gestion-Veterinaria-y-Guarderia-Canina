import { useEffect, useState } from 'react';
import { Link, NavLink } from 'react-router-dom';

import { listarReservas } from '../../modules/guarderia/api';
import type { Sesion } from '../auth/almacenSesion';
import { etiquetaRol, type Seccion } from '../auth/permisos';
import { PatitaIcon } from '../components/PatitaIcon';
import { SeccionIcon } from './SeccionIcon';
import estilos from './Sidebar.module.css';

type Props = {
  sesion: Sesion;
  secciones: readonly Seccion[];
  inicio: string;
  contadorDeudores: number | null;
  onSalir: () => void;
};

function fechaIsoLocal(fecha: Date): string {
  const mes = String(fecha.getMonth() + 1).padStart(2, '0');
  const dia = String(fecha.getDate()).padStart(2, '0');

  return `${fecha.getFullYear()}-${mes}-${dia}`;
}

export function Sidebar({
  sesion,
  secciones,
  inicio,
  contadorDeudores,
  onSalir,
}: Props) {
  const [huellitasEnCasa, setHuellitasEnCasa] = useState<number | null>(null);

  useEffect(() => {
    const controlador = new AbortController();
    let activo = true;
    const hoy = fechaIsoLocal(new Date());

    listarReservas(hoy, hoy, { signal: controlador.signal })
      .then((reservas) => {
        if (!activo || controlador.signal.aborted) {
          return;
        }

        const pacientes = new Set<number>();

        reservas
          .filter(
            (reserva) =>
              reserva.estado === 'CONFIRMADA' ||
              reserva.estado === 'EN_CURSO',
          )
          .forEach((reserva) => {
            reserva.pacientes.forEach((paciente) =>
              pacientes.add(paciente.paciente_id),
            );
          });

        setHuellitasEnCasa(pacientes.size);
      })
      .catch(() => {
        if (activo && !controlador.signal.aborted) {
          setHuellitasEnCasa(null);
        }
      });

    return () => {
      activo = false;
      controlador.abort();
    };
  }, []);

  return (
    <aside className={estilos.sidebar}>
      <div className={estilos.interior}>
        <Link className={estilos.marca} to={inicio} aria-label="Huellitas, ir al inicio">
          <span className={estilos.monograma} aria-hidden="true">
            <PatitaIcon />
          </span>
          <span className={estilos.marcaTexto}>
            <span className={estilos.marcaNombre}>Huellitas</span>
            <span className={estilos.marcaBajada}>Veterinaria y guardería</span>
          </span>
        </Link>

        <nav className={estilos.nav} aria-label="Navegación lateral">
          <ul>
            {secciones.map((seccion) => {
              const contador =
                seccion.id === 'deudores' ? contadorDeudores : null;

              return (
                <li key={seccion.id}>
                  <NavLink
                    aria-label={
                      contador ? `${seccion.etiqueta}: ${contador}` : undefined
                    }
                    className={({ isActive }) =>
                      [estilos.enlace, isActive ? estilos.activo : null]
                        .filter(Boolean)
                        .join(' ')
                    }
                    end
                    to={seccion.ruta}
                  >
                    <span className={estilos.icono}>
                      <SeccionIcon seccion={seccion.id} />
                    </span>
                    <span className={estilos.enlaceTexto}>{seccion.etiqueta}</span>
                    {contador ? (
                      <span aria-hidden="true" className={estilos.contador}>
                        {contador}
                      </span>
                    ) : null}
                  </NavLink>
                </li>
              );
            })}
          </ul>
        </nav>

        <div className={estilos.mascota}>
          <img src="/images/mascotas.png" alt="" />
          <p>Hola, {sesion.usuario}!</p>
          {huellitasEnCasa !== null ? (
            <p>Hoy hay {huellitasEnCasa} huellitas en casa</p>
          ) : null}
        </div>

        <div className={estilos.pie}>
          <div>
            <p className={estilos.usuario}>{sesion.usuario}</p>
            <p className={estilos.rol}>{etiquetaRol(sesion.rol)}</p>
          </div>
          <button className={estilos.botonSalir} type="button" onClick={onSalir}>
            Cerrar sesión
          </button>
        </div>
      </div>
    </aside>
  );
}
