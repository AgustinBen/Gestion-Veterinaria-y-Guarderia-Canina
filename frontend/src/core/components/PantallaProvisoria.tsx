import type { SeccionId } from '../auth/permisos';
import { useAuth } from '../auth/contexto';
import { puedeAcceder } from '../auth/permisos';
import { SeccionIcon } from '../layout/SeccionIcon';
import estilos from './PantallaProvisoria.module.css';

type Props = {
  seccion: SeccionId;
  titulo: string;
  descripcion: string;
};

const ETIQUETA_SECCION: Partial<Record<SeccionId, string>> = {
  panel: 'Panel del dueño',
  calendario: 'Guardería y clínica',
  'nueva-reserva': 'Nuevo registro',
  turnos: 'Agenda veterinaria',
  'historia-clinica': 'Ficha completa',
  migracion: 'Datos históricos',
};

function diasDelMesActual(): (number | null)[] {
  const hoy = new Date();
  const inicio = new Date(hoy.getFullYear(), hoy.getMonth(), 1);
  const espaciosPrevios = (inicio.getDay() + 6) % 7;
  const cantidad = new Date(hoy.getFullYear(), hoy.getMonth() + 1, 0).getDate();

  return [
    ...Array.from({ length: espaciosPrevios }, () => null),
    ...Array.from({ length: cantidad }, (_, indice) => indice + 1),
  ];
}

function VistaPrevia({ seccion }: { seccion: SeccionId }) {
  switch (seccion) {
    case 'panel':
      return (
        <section
          aria-label="Métricas del negocio"
          className={`${estilos.vista} ${estilos.vistaPanel}`}
        >
          <div className={estilos.vistaEncabezado}>
            <div>
              <h2>Métricas del negocio</h2>
            </div>
            <div className={estilos.periodos} aria-label="Períodos del resumen">
              <span className={estilos.etiquetaVista}>Mensual</span>
              <span className={estilos.etiquetaVista}>Anual</span>
            </div>
          </div>
          <div className={estilos.metricas}>
            {['Ingresos', 'Gastos', 'Balance'].map((metrica) => (
              <article className={estilos.metrica} key={metrica}>
                <span>{metrica}</span>
                <strong aria-label={`${metrica}: sin valor`}>—</strong>
                <small>Período actual</small>
              </article>
            ))}
          </div>
          <div className={estilos.graficoVacio}>
            <span className={estilos.vistaAntetitulo}>Actividad mensual</span>
            <div className={estilos.barras} aria-hidden="true">
              <i /><i /><i /><i /><i /><i /><i />
            </div>
          </div>
        </section>
      );
    case 'calendario': {
      const hoy = new Date();
      const mesActual = new Intl.DateTimeFormat('es-AR', {
        month: 'long',
        year: 'numeric',
      }).format(hoy);
      const dias = diasDelMesActual();

      return (
        <section
          aria-label="Calendario de guardería"
          className={`${estilos.vista} ${estilos.vistaCalendario}`}
        >
          <div className={estilos.vistaEncabezado}>
            <div>
              <p className={estilos.vistaAntetitulo}>Guardería</p>
              <h2>{mesActual}</h2>
            </div>
            <span className={estilos.etiquetaVista}>Cupo por franja</span>
          </div>
          <div className={estilos.calendario}>
            {['Lu', 'Ma', 'Mi', 'Ju', 'Vi', 'Sá', 'Do'].map((dia) => (
              <span className={estilos.diaSemana} key={dia}>{dia}</span>
            ))}
            {dias.map((dia, indice) => (
              <span
                aria-current={dia === hoy.getDate() ? 'date' : undefined}
                className={dia === null ? estilos.diaVacio : estilos.diaMes}
                key={`${dia ?? 'vacio'}-${indice}`}
              >
                {dia}
              </span>
            ))}
          </div>
          <div className={estilos.leyenda}>
            <span><i className={estilos.muestraDia} /> Día</span>
            <span><i className={estilos.muestraNoche} /> Noche</span>
          </div>
        </section>
      );
    }
    case 'nueva-reserva':
      return (
        <section
          aria-label="Nueva reserva de guardería"
          className={`${estilos.vista} ${estilos.vistaReserva}`}
        >
          <div className={estilos.vistaEncabezado}>
            <div>
              <p className={estilos.vistaAntetitulo}>Guardería</p>
              <h2>Datos de la estadía</h2>
            </div>
            <span className={estilos.etiquetaVista}>Nueva reserva</span>
          </div>
          <div className={estilos.reservaVista}>
            <div className={estilos.camposVista}>
              {['Mascota', 'Tutor', 'Fecha de ingreso', 'Fecha de egreso', 'Franja', 'Seña'].map((campo) => (
                <div className={estilos.campoVista} key={campo}>
                  <span>{campo}</span>
                  <div aria-hidden="true"><i /></div>
                </div>
              ))}
            </div>
            <aside className={estilos.resumenVista}>
              <h3>Resumen de la reserva</h3>
              <p><span>Duración</span><strong>—</strong></p>
              <p><span>Cuidados extras</span><strong>—</strong></p>
              <p><span>Total</span><strong>—</strong></p>
              <p><span>Seña</span><strong>—</strong></p>
            </aside>
          </div>
        </section>
      );
    case 'turnos':
      return (
        <section
          aria-label="Agenda de turnos"
          className={`${estilos.vista} ${estilos.vistaTurnos}`}
        >
          <div className={estilos.vistaEncabezado}>
            <div>
              <p className={estilos.vistaAntetitulo}>Agenda</p>
              <h2>Turnos del día</h2>
            </div>
            <span className={estilos.etiquetaVista}>Mañana · Tarde · Noche</span>
          </div>
          <div className={estilos.turnos}>
            {['Mañana', 'Tarde', 'Noche'].map((turno) => (
              <article className={estilos.turno} key={turno}>
                <h3>{turno}</h3>
                <div aria-hidden="true"><i /><i /></div>
              </article>
            ))}
          </div>
        </section>
      );
    case 'historia-clinica':
      return (
        <section
          aria-label="Historia clínica"
          className={`${estilos.vista} ${estilos.vistaHistoria}`}
        >
          <div className={estilos.vistaEncabezado}>
            <div>
              <p className={estilos.vistaAntetitulo}>Historia clínica</p>
              <h2>Elegí una mascota</h2>
            </div>
            <span className={estilos.etiquetaVista}>Consultas y tratamientos</span>
          </div>
          <div className={estilos.busquedaVista} aria-hidden="true">
            <SeccionIcon seccion="padron" />
            <span>Buscar por nombre de mascota</span>
          </div>
          <div className={estilos.categoriasClinicas}>
            {['Consultas', 'Vacunas', 'Cirugías', 'Tratamientos'].map((categoria) => (
              <span key={categoria}>{categoria}</span>
            ))}
          </div>
        </section>
      );
    case 'migracion':
      return (
        <section
          aria-label="Migración de datos"
          className={`${estilos.vista} ${estilos.vistaMigracion}`}
        >
          <div className={estilos.vistaEncabezado}>
            <div>
              <p className={estilos.vistaAntetitulo}>Datos históricos</p>
              <h2>Importar archivo</h2>
            </div>
            <span className={estilos.etiquetaVista}>Excel</span>
          </div>
          <div className={estilos.zonaArchivo}>
            <span className={estilos.archivoIcono} aria-hidden="true">
              <SeccionIcon seccion="migracion" />
            </span>
            <strong>Arrastrá tu archivo Excel aquí</strong>
            <span>o elegí un archivo de tu equipo</span>
          </div>
          <div className={estilos.pasosMigracion}>
            {['Archivo', 'Validación', 'Revisión'].map((paso, indice) => (
              <span key={paso}><i>{indice + 1}</i>{paso}</span>
            ))}
          </div>
        </section>
      );
    default:
      return null;
  }
}

export function PantallaProvisoria({ seccion, titulo, descripcion }: Props) {
  const { sesion } = useAuth();
  const soloLectura = sesion ? !puedeAcceder(sesion.rol, seccion, 'escritura') : false;

  return (
    <section className={estilos.pagina} aria-labelledby={`titulo-${seccion}`}>
      <header className={estilos.cabecera}>
        <div className={estilos.introduccion}>
          <p className={estilos.antetitulo}>{ETIQUETA_SECCION[seccion] ?? titulo}</p>
          <div className={estilos.filaTitulo}>
            <h1 id={`titulo-${seccion}`}>{titulo}</h1>
            {soloLectura ? <span className={estilos.insignia}>Solo lectura</span> : null}
          </div>
          <p className={estilos.descripcion}>{descripcion}</p>
        </div>
      </header>

      <VistaPrevia seccion={seccion} />
    </section>
  );
}
