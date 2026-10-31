import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { Alerta } from '../../../core/components/ui/Alerta';
import { Boton } from '../../../core/components/ui/Boton';
import { ChipFranja } from '../components/ChipFranja';
import {
  espaciosAntesDelMes,
  fechaLocal,
  fechasDelMes,
  formatearFecha,
  primerDiaDelMes,
  sumarMeses,
} from '../fechas';
import { listarCalendario, mensajeDeError } from '../api';
import { usePuedeEscribirReservas } from '../permisos';
import type { Disponibilidad, Franja } from '../tipos';
import estilos from '../guarderia.module.css';

type EstadoCarga = 'listo' | 'error';

type CargaCalendario = {
  clave: string;
  estado: EstadoCarga;
  datos: Disponibilidad[];
  error: string;
};

const FRANJAS: Franja[] = ['DIA', 'NOCHE'];
const DIAS_SEMANA = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];

export function Calendario() {
  const puedeEscribir = usePuedeEscribirReservas();
  const [desplazamientoMes, setDesplazamientoMes] = useState(0);
  const [intento, setIntento] = useState(0);
  const [carga, setCarga] = useState<CargaCalendario | null>(null);
  const [franjaSeleccionada, setFranjaSeleccionada] = useState<string | null>(null);

  const primerDia = useMemo(
    () => sumarMeses(primerDiaDelMes(new Date()), desplazamientoMes),
    [desplazamientoMes],
  );
  const fechas = useMemo(() => fechasDelMes(primerDia), [primerDia]);
  const desde = fechaLocal(primerDia);
  const hasta = fechaLocal(fechas[fechas.length - 1]!);
  const clave = `${desde}:${hasta}:${intento}`;

  useEffect(() => {
    const control = new AbortController();
    let activo = true;

    listarCalendario(desde, hasta, { signal: control.signal })
      .then((datos) => {
        if (!activo || control.signal.aborted) {
          return;
        }

        setCarga({ clave, estado: 'listo', datos, error: '' });
      })
      .catch((fallo: unknown) => {
        if (!activo || control.signal.aborted) {
          return;
        }

        setCarga({
          clave,
          estado: 'error',
          datos: [],
          error: mensajeDeError(fallo),
        });
      });

    return () => {
      activo = false;
      control.abort();
    };
  }, [clave, desde, hasta]);

  const vigente = carga?.clave === clave ? carga : null;
  const disponiblesPorClave = new Map(
    (vigente?.datos ?? []).map((dato) => [`${dato.fecha}:${dato.franja}`, dato]),
  );
  const celdasVacias = espaciosAntesDelMes(primerDia);

  function alternarFranja(fecha: string, franja: Franja) {
    const claveFranja = `${fecha}:${franja}`;
    setFranjaSeleccionada((actual) => (actual === claveFranja ? null : claveFranja));
  }

  const mes = formatearFecha(primerDia, { month: 'long', year: 'numeric' });

  return (
    <section aria-labelledby="titulo-calendario" className={estilos.pagina}>
      <header className={estilos.cabecera}>
        <div>
          <h1 className={estilos.titulo} id="titulo-calendario">
            Calendario de cupo
          </h1>
          <p className={estilos.subtitulo}>Disponibilidad pública por día y franja.</p>
        </div>
        {puedeEscribir ? (
          <Link className={estilos.botonEnlace} to="/guarderia/reservar">
            Nueva reserva
          </Link>
        ) : null}
      </header>

      <nav aria-label="Navegar meses" className={estilos.navegacion}>
        <Boton
          aria-label="Mes anterior"
          onClick={() => {
            setDesplazamientoMes((valor) => valor - 1);
            setFranjaSeleccionada(null);
          }}
          variante="secundario"
        >
          Anterior
        </Boton>
        <h2 aria-live="polite" className={estilos.rango}>
          {mes}
        </h2>
        <Boton
          aria-label="Mes siguiente"
          onClick={() => {
            setDesplazamientoMes((valor) => valor + 1);
            setFranjaSeleccionada(null);
          }}
          variante="secundario"
        >
          Siguiente
        </Boton>
      </nav>

      {!vigente ? (
        <p className={estilos.cargando} role="status">
          Cargando calendario…
        </p>
      ) : vigente.estado === 'error' ? (
        <Alerta
          acciones={
            <Boton onClick={() => setIntento((valor) => valor + 1)} variante="secundario">
              Reintentar
            </Boton>
          }
          role="alert"
          tono="error"
        >
          {vigente.error}
        </Alerta>
      ) : (
        <>
          {vigente.datos.length === 0 ? (
            <p className={estilos.vacio}>No hay datos de cupo para este mes.</p>
          ) : null}
          <div aria-label="Estados de ocupación" className={estilos.leyendaCalendario}>
            <span className={estilos.leyendaConLugar}>Con lugar</span>
            <span className={estilos.leyendaCompleto}>Completo</span>
            <span>D: Día · N: Noche · ocupadas/cupo público</span>
          </div>
          <div aria-label="Calendario mensual" className={estilos.calendarioMensual}>
            {DIAS_SEMANA.map((dia) => (
              <span className={estilos.encabezadoDiaSemana} key={dia}>
                {dia}
              </span>
            ))}
            {Array.from({ length: celdasVacias }, (_, indice) => (
              <span aria-hidden="true" className={estilos.celdaVacia} key={`vacia-${indice}`} />
            ))}
            {fechas.map((fecha) => {
              const fechaTexto = fechaLocal(fecha);
              const fechaAccesible = formatearFecha(fecha, {
                day: 'numeric',
                month: 'long',
              });

              return (
                <article className={estilos.dia} key={fechaTexto}>
                  <h3 className={estilos.diaTitulo}>
                    {puedeEscribir ? (
                      <Link
                        aria-label={`Reservar ${fechaAccesible}`}
                        className={estilos.enlaceDia}
                        to={`/guarderia/reservar?fecha=${fechaTexto}`}
                      >
                        {fecha.getDate()}
                      </Link>
                    ) : (
                      <span>{fecha.getDate()}</span>
                    )}
                  </h3>
                  <div className={estilos.chips}>
                    {FRANJAS.map((franja) => {
                      const claveFranja = `${fechaTexto}:${franja}`;

                      return (
                        <ChipFranja
                          disponibilidad={disponiblesPorClave.get(claveFranja) ?? null}
                          franja={franja}
                          key={franja}
                          onSeleccionar={() => alternarFranja(fechaTexto, franja)}
                          seleccionada={franjaSeleccionada === claveFranja}
                        />
                      );
                    })}
                  </div>
                </article>
              );
            })}
          </div>
        </>
      )}
    </section>
  );
}
