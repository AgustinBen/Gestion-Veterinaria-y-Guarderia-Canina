import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';

import { Alerta } from '../../../core/components/ui/Alerta';
import { Boton } from '../../../core/components/ui/Boton';
import { listarEmpleados, listarPacientes } from '../../padron/api';
import type { EmpleadoDetalle, PacienteResumen } from '../../padron/tipos';
import { listarIdsVeterinarios, mensajeDeError } from '../api';
import { NuevoTurno } from '../components/NuevoTurno';
import { fechaLocal } from '../fechas';
import estilos from '../clinica.module.css';

const MAX_PACIENTES = 100;

type Estado = 'cargando' | 'listo' | 'error';

export function NuevoTurnoPage() {
  const navegar = useNavigate();
  const [parametros] = useSearchParams();
  const fechaParametro = parametros.get('fecha') ?? '';
  const fechaInicial = /^\d{4}-\d{2}-\d{2}$/.test(fechaParametro)
    ? fechaParametro
    : fechaLocal(new Date());
  const [pacientes, setPacientes] = useState<PacienteResumen[]>([]);
  const [empleados, setEmpleados] = useState<EmpleadoDetalle[]>([]);
  const [estado, setEstado] = useState<Estado>('cargando');
  const [error, setError] = useState('');
  const [intento, setIntento] = useState(0);

  useEffect(() => {
    const controlador = new AbortController();
    let activo = true;

    async function cargar() {
      setEstado('cargando');
      setError('');

      try {
        const [datosPacientes, datosEmpleados, idsVeterinarios] =
          await Promise.all([
            listarPacientes({
              limite: MAX_PACIENTES,
              signal: controlador.signal,
            }),
            listarEmpleados({ signal: controlador.signal }),
            listarIdsVeterinarios({ signal: controlador.signal }),
          ]);

        if (activo) {
          const veterinariosUsuario = new Set(idsVeterinarios);
          const empleadosNormalizados = datosEmpleados.map((empleado) => {
            return {
              ...empleado,
              es_veterinario: veterinariosUsuario.has(empleado.persona_id),
            };
          });

          setPacientes(datosPacientes);
          setEmpleados(empleadosNormalizados);
          setEstado('listo');
        }
      } catch (fallo) {
        if (!activo || controlador.signal.aborted) {
          return;
        }

        setError(mensajeDeError(fallo));
        setEstado('error');
      }
    }

    void cargar();

    return () => {
      activo = false;
      controlador.abort();
    };
  }, [intento]);

  return (
    <section className={estilos.pagina} aria-labelledby="titulo-nuevo-turno">
      <header className={estilos.cabecera}>
        <div className={estilos.introduccion}>
          <p className={estilos.antetitulo}>Agenda veterinaria</p>
          <h1 className={estilos.titulo} id="titulo-nuevo-turno">
            Nuevo turno
          </h1>
          <p className={estilos.subtitulo}>
            Elegí la mascota, el veterinario y el horario. El sistema valida el
            horario de atención y los turnos superpuestos.
          </p>
        </div>
        <Link className={estilos.enlace} to="/turnos">
          Volver a la agenda
        </Link>
      </header>

      {estado === 'cargando' ? (
        <section className={estilos.panel}>
          <p className={estilos.cargando}>Cargando mascotas y veterinarios…</p>
        </section>
      ) : estado === 'error' ? (
        <section className={estilos.panel}>
          <Alerta
            acciones={
              <Boton
                onClick={() => setIntento((actual) => actual + 1)}
                variante="secundario"
              >
                Reintentar
              </Boton>
            }
            role="alert"
            tono="error"
          >
            {error}
          </Alerta>
        </section>
      ) : (
        <NuevoTurno
          empleados={empleados}
          fechaInicial={fechaInicial}
          onCancelar={() => navegar('/turnos')}
          onCreado={(turno) => navegar(`/turnos/${turno.id}`)}
          pacientes={pacientes}
        />
      )}
    </section>
  );
}
