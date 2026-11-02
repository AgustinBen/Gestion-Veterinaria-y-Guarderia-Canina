import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { EmpleadoDetalle } from '../../padron/tipos';
import {
  crearEstudio,
  eliminarAdjunto,
  listarEstudios,
  subirAdjunto,
} from '../api';
import { SubidaPlacas } from '../components/SubidaPlacas';
import type { AdjuntoResumen, EstudioResumen } from '../tipos';

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>();

  return {
    ...actual,
    crearEstudio: vi.fn(),
    eliminarAdjunto: vi.fn(),
    listarEstudios: vi.fn(),
    subirAdjunto: vi.fn(),
  };
});

const EMPLEADOS: EmpleadoDetalle[] = [
  {
    persona_id: 7,
    nombre: 'Ana',
    apellido: 'Paz',
    dni: null,
    dni_pendiente: true,
    telefonos: [],
    tipo: 'INTERNO',
    es_veterinario: true,
    especialidad: null,
    email: null,
    activo: true,
  },
];

const ESTUDIO: EstudioResumen = {
  id: 5,
  paciente_id: 3,
  atencion_id: null,
  tipo: 'RADIOGRAFIA',
  fecha: '2026-10-01',
  descripcion: 'Placa de tórax',
  realizado_por_empleado_id: 7,
  cargo_id: null,
  created_by: 1,
  created_at: '2026-10-01T10:00:00',
  adjuntos: [],
};

const ADJUNTO: AdjuntoResumen = {
  id: 8,
  nombre_original: 'placa.png',
  tipo_mime: 'image/png',
  tamano_bytes: 10,
  sha256: 'abc',
  created_by: 1,
  created_at: '2026-10-01T10:05:00',
};

describe('SubidaPlacas', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(listarEstudios).mockResolvedValue([]);
  });

  it('registra un estudio y permite subir un archivo con progreso', async () => {
    const crearMock = vi.mocked(crearEstudio);
    const subirMock = vi.mocked(subirAdjunto);
    crearMock.mockResolvedValue(ESTUDIO);
    subirMock.mockResolvedValue(ADJUNTO);

    render(
      <SubidaPlacas
        empleados={EMPLEADOS}
        pacienteId={3}
        puedeEscribir
      />,
    );

    expect(
      await screen.findByText('Todavía no hay estudios cargados.'),
    ).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Descripción'), {
      target: { value: 'Placa de tórax' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Registrar estudio' }));

    await waitFor(() => {
      expect(crearMock).toHaveBeenCalledWith(
        3,
        expect.objectContaining({
          tipo: 'RADIOGRAFIA',
          descripcion: 'Placa de tórax',
          realizado_por_empleado_id: 7,
        }),
      );
    });

    expect(await screen.findByText('Placa de tórax')).toBeInTheDocument();

    const archivo = new File(['contenido'], 'placa.png', {
      type: 'image/png',
    });
    fireEvent.change(
      screen.getByLabelText('Adjuntar archivo al estudio 5'),
      { target: { files: [archivo] } },
    );

    await waitFor(() => {
      expect(subirMock).toHaveBeenCalledWith(
        5,
        archivo,
        expect.objectContaining({ onProgreso: expect.any(Function) }),
      );
    });

    expect(await screen.findByText('placa.png')).toBeInTheDocument();
  });

  it('elimina un adjunto cargado por error tras confirmar', async () => {
    vi.mocked(listarEstudios).mockResolvedValue([
      { ...ESTUDIO, adjuntos: [ADJUNTO] },
    ]);
    vi.mocked(eliminarAdjunto).mockResolvedValue(undefined);

    render(
      <SubidaPlacas empleados={EMPLEADOS} pacienteId={3} puedeEscribir />,
    );

    fireEvent.click(
      await screen.findByRole('button', { name: 'Eliminar placa.png' }),
    );
    // No se borra hasta confirmar.
    expect(eliminarAdjunto).not.toHaveBeenCalled();

    fireEvent.click(
      screen.getByRole('button', { name: 'Confirmar eliminación' }),
    );

    await waitFor(() => expect(eliminarAdjunto).toHaveBeenCalledWith(8));
    await waitFor(() =>
      expect(screen.queryByText('placa.png')).not.toBeInTheDocument(),
    );
    expect(screen.getByText('Sin archivos adjuntos.')).toBeInTheDocument();
  });

  it('permite cancelar la eliminación y la oculta en modo lectura', async () => {
    vi.mocked(listarEstudios).mockResolvedValue([
      { ...ESTUDIO, adjuntos: [ADJUNTO] },
    ]);

    const { unmount } = render(
      <SubidaPlacas empleados={EMPLEADOS} pacienteId={3} puedeEscribir />,
    );
    fireEvent.click(
      await screen.findByRole('button', { name: 'Eliminar placa.png' }),
    );
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }));

    expect(eliminarAdjunto).not.toHaveBeenCalled();
    expect(screen.getByText('placa.png')).toBeInTheDocument();
    unmount();

    render(
      <SubidaPlacas
        empleados={EMPLEADOS}
        pacienteId={3}
        puedeEscribir={false}
      />,
    );
    await screen.findByText('placa.png');
    expect(
      screen.queryByRole('button', { name: /Eliminar/ }),
    ).not.toBeInTheDocument();
  });

  it('no muestra el formulario de alta en modo lectura', async () => {
    render(
      <SubidaPlacas
        empleados={EMPLEADOS}
        pacienteId={3}
        puedeEscribir={false}
      />,
    );

    await screen.findByText('Todavía no hay estudios cargados.');

    expect(screen.queryByLabelText('Descripción')).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: 'Registrar estudio' }),
    ).not.toBeInTheDocument();
  });
});
