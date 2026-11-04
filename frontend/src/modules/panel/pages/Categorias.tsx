import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';

import { Alerta } from '../../../core/components/ui/Alerta';
import { Boton } from '../../../core/components/ui/Boton';
import { Campo } from '../../../core/components/ui/Campo';
import {
  actualizarCategoriaEgreso,
  crearCategoriaEgreso,
  listarCategoriasEgreso,
  mensajeDeError,
} from '../api';
import type { CategoriaEgreso } from '../tipos';
import estilos from '../panel.module.css';

type Estado =
  | { estado: 'cargando' }
  | { estado: 'error'; error: string }
  | { estado: 'listo'; categorias: CategoriaEgreso[] };

/** Alta, activación y desactivación de categorías de egreso (T-38). */
export function Categorias() {
  const [carga, setCarga] = useState<Estado>({ estado: 'cargando' });
  const [reintento, setReintento] = useState(0);
  const [nombre, setNombre] = useState('');
  const [errorAlta, setErrorAlta] = useState('');
  const [enviando, setEnviando] = useState(false);
  const enviandoRef = useRef(false);

  useEffect(() => {
    const control = new AbortController();

    listarCategoriasEgreso({ signal: control.signal })
      .then((categorias) => {
        if (!control.signal.aborted) {
          setCarga({ estado: 'listo', categorias });
        }
      })
      .catch((fallo) => {
        if (!control.signal.aborted) {
          setCarga({ estado: 'error', error: mensajeDeError(fallo) });
        }
      });

    return () => control.abort();
  }, [reintento]);

  async function crear(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();

    if (enviandoRef.current) {
      return;
    }

    if (!nombre.trim()) {
      setErrorAlta('Escribí un nombre para la categoría.');
      return;
    }

    enviandoRef.current = true;
    setEnviando(true);
    setErrorAlta('');

    try {
      await crearCategoriaEgreso(nombre.trim());
      setNombre('');
      setReintento((valor) => valor + 1);
    } catch (fallo) {
      setErrorAlta(mensajeDeError(fallo));
    } finally {
      enviandoRef.current = false;
      setEnviando(false);
    }
  }

  async function alternar(categoria: CategoriaEgreso) {
    try {
      await actualizarCategoriaEgreso(categoria.id, !categoria.activa);
      setReintento((valor) => valor + 1);
    } catch (fallo) {
      setCarga({ estado: 'error', error: mensajeDeError(fallo) });
    }
  }

  return (
    <div className={estilos.pagina}>
      <div className={`${estilos.cabecera} ${estilos.cabeceraCobros}`}>
        <div>
          <p className={estilos.antetitulo}>Panel financiero</p>
          <h1 className={estilos.titulo}>Categorías de egreso</h1>
          <p className={estilos.subtitulo}>
            Organizá los egresos operativos por categoría.
          </p>
          <Link
            className={`${estilos.enlace} ${estilos.volver}`}
            to="/panel/egresos"
          >
            Volver a egresos
          </Link>
        </div>
      </div>

      <section aria-label="Nueva categoría" className={estilos.tarjeta}>
        <h2>Crear categoría</h2>
        <form className={estilos.formulario} onSubmit={crear}>
          <Campo
            ayuda="Por ejemplo: Insumos, Servicios, Sueldos."
            error={errorAlta}
            etiqueta="Nombre"
            id="categoria-nombre"
            obligatorio
          >
            <input
              id="categoria-nombre"
              onChange={(evento) => setNombre(evento.target.value)}
              value={nombre}
            />
          </Campo>
          <Boton cargando={enviando} type="submit">
            Crear categoría
          </Boton>
        </form>
      </section>

      {carga.estado === 'cargando' ? (
        <p role="status">Cargando categorías…</p>
      ) : null}

      {carga.estado === 'error' ? (
        <Alerta
          acciones={
            <Boton
              onClick={() => setReintento((valor) => valor + 1)}
              variante="secundario"
            >
              Reintentar
            </Boton>
          }
          role="alert"
          tono="error"
        >
          {carga.error}
        </Alerta>
      ) : null}

      {carga.estado === 'listo' ? (
        carga.categorias.length === 0 ? (
          <p className={estilos.textoSuave}>
            Todavía no hay categorías. Creá la primera para poder registrar
            egresos.
          </p>
        ) : (
          <div className={estilos.tablaContenedor}>
            <table className={estilos.tabla}>
              <caption>Categorías de egreso</caption>
              <thead>
                <tr>
                  <th scope="col">Nombre</th>
                  <th scope="col">Estado</th>
                  <th scope="col">Acción</th>
                </tr>
              </thead>
              <tbody>
                {carga.categorias.map((categoria) => (
                  <tr key={categoria.id}>
                    <th scope="row">{categoria.nombre}</th>
                    <td>{categoria.activa ? 'Activa' : 'Inactiva'}</td>
                    <td>
                      <Boton
                        onClick={() => alternar(categoria)}
                        variante="secundario"
                      >
                        {categoria.activa ? 'Desactivar' : 'Activar'}
                      </Boton>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      ) : null}
    </div>
  );
}
