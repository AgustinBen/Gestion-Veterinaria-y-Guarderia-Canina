import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { EmpleadoDetalle } from '../../padron/tipos';
import { crearAtencion } from '../api';
import { FormularioAtencion } from '../components/FormularioAtencion';
import type { AtencionDetalle } from '../tipos';

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>();

  return {
    ...actual,
    crearAtencion: vi.fn(),
    rectificarAtencion: vi.fn(),
  };
});

const EMPLEADOS: EmpleadoDetalle[] = [
  {
    persona_id: 7,
    nombre: 'Ana',
    apellido: 'Paz',
    dni: '30000001',
    dni_pendiente: false,
    telefonos: [],
    tipo: 'INTERNO',
    es_veterinario: true,
    especialidad: 'Clínica',
    email: null,
    activo: true,
  },
  {
    persona_id: 9,
    nombre: 'Mario',
    apellido: 'Sosa',
    dni: '30000002',
    dni_pendiente: false,
    telefonos: [],
    tipo: 'EXTERNO',
    es_veterinario: true,
    especialidad: 'Cirugía',
    email: null,
    activo: true,
  },
];

const ATENCION_GUARDADA: AtencionDetalle = {
  id: 20,
  paciente_id: 3,
  tipo: 'VACUNA',
  fecha_hora: '2026-10-01T10:00:00',
  veterinario_empleado_id: 7,
  veterinario_nombre: 'Ana Paz',
  motivo: null,
  diagnostico: null,
  tratamiento: null,
  observaciones: null,
  cirujano_externo_id: null,
  cirujano_externo_nombre: null,
  cargo_id: null,
  origen: 'NORMAL',
  texto_original: null,
  rectifica_a_id: null,
  rectificada: false,
  created_by: 1,
  created_at: '2026-10-01T10:00:00',
  vacuna: {
    id: 1,
    atencion_id: 20,
    nombre_vacuna: 'Quíntuple',
    lote: null,
    fecha_aplicacion: '2026-10-01',
    proxima_dosis: null,
  },
};

describe('FormularioAtencion', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('registra una vacuna con veterinario, fecha y nombre', async () => {
    const crearMock = vi.mocked(crearAtencion);
    crearMock.mockResolvedValue(ATENCION_GUARDADA);
    const onGuardado = vi.fn();

    render(
      <FormularioAtencion
        empleados={EMPLEADOS}
        onGuardado={onGuardado}
        pacienteId={3}
      />,
    );

    fireEvent.change(screen.getByLabelText('Tipo de atención'), {
      target: { value: 'VACUNA' },
    });
    fireEvent.change(screen.getByLabelText('Nombre de la vacuna'), {
      target: { value: 'Quíntuple' },
    });
    fireEvent.change(screen.getByLabelText('Fecha de aplicación'), {
      target: { value: '2026-10-01' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Guardar atención' }));

    await waitFor(() => {
      expect(crearMock).toHaveBeenCalledWith(
        3,
        expect.objectContaining({
          tipo: 'VACUNA',
          veterinario_empleado_id: 7,
          vacuna: expect.objectContaining({
            nombre_vacuna: 'Quíntuple',
            fecha_aplicacion: '2026-10-01',
          }),
        }),
      );
    });

    await waitFor(() => {
      expect(onGuardado).toHaveBeenCalledWith(ATENCION_GUARDADA);
    });
  });

  it('exige un cirujano externo cuando la atención es una cirugía', async () => {
    const crearMock = vi.mocked(crearAtencion);

    render(
      <FormularioAtencion
        empleados={EMPLEADOS}
        onGuardado={vi.fn()}
        pacienteId={3}
      />,
    );

    fireEvent.change(screen.getByLabelText('Tipo de atención'), {
      target: { value: 'CIRUGIA' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Guardar atención' }));

    expect(
      await screen.findByText('La cirugía requiere un cirujano externo.'),
    ).toBeInTheDocument();
    expect(crearMock).not.toHaveBeenCalled();
  });
});
