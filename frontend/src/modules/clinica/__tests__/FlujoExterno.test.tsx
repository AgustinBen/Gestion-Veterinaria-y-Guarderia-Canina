import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { EmpleadoDetalle } from '../../padron/tipos';
import {
  confirmarExterno,
  contactarExterno,
  listarEventosExterno,
} from '../api';
import { FlujoExterno } from '../components/FlujoExterno';
import type { EventoExterno } from '../tipos';

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>();

  return {
    ...actual,
    confirmarExterno: vi.fn(),
    contactarExterno: vi.fn(),
    listarEventosExterno: vi.fn(),
  };
});

const EXTERNOS: EmpleadoDetalle[] = [
  {
    persona_id: 9,
    nombre: 'Mario',
    apellido: 'Sosa',
    dni: null,
    dni_pendiente: true,
    telefonos: [],
    tipo: 'EXTERNO',
    es_veterinario: true,
    especialidad: 'Cirugía',
    email: null,
    activo: true,
  },
];

const EVENTO_CONTACTO: EventoExterno = {
  id: 30,
  turno_id: 12,
  tipo: 'CONTACTADO',
  externo_empleado_id: 9,
  externo_nombre: 'Mario Sosa',
  medio: 'TELEFONO',
  nota: 'Llamado',
  costo_acordado_centavos: null,
  costo_registrado: false,
  usuario_id: 1,
  created_at: '2026-10-30T10:00:00',
};

const EVENTO_CONFIRMADO: EventoExterno = {
  ...EVENTO_CONTACTO,
  id: 31,
  tipo: 'CONFIRMADO',
  costo_acordado_centavos: 1000000,
  costo_registrado: true,
};

describe('FlujoExterno', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(listarEventosExterno).mockResolvedValue([]);
  });

  it('carga los eventos y registra un contacto sin ofrecer confirmar el costo a un rol sin permiso', async () => {
    const contactarMock = vi.mocked(contactarExterno);
    contactarMock.mockResolvedValue(EVENTO_CONTACTO);
    const onEvento = vi.fn();

    render(
      <FlujoExterno
        empleados={EXTERNOS}
        onEvento={onEvento}
        puedeConfirmarCosto={false}
        turnoId={12}
      />,
    );

    expect(
      await screen.findByText('Sin eventos registrados.'),
    ).toBeInTheDocument();
    expect(listarEventosExterno).toHaveBeenCalledWith(12, expect.anything());
    expect(
      screen.queryByRole('button', { name: 'Confirmar costo' }),
    ).not.toBeInTheDocument();

    fireEvent.click(
      screen.getByRole('button', { name: 'Registrar contacto' }),
    );
    fireEvent.change(screen.getByLabelText('Nota (opcional)'), {
      target: { value: 'Llamado' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }));

    await waitFor(() => {
      expect(contactarMock).toHaveBeenCalledWith(12, {
        medio: 'TELEFONO',
        nota: 'Llamado',
      });
    });

    await waitFor(() => {
      expect(onEvento).toHaveBeenCalledWith(EVENTO_CONTACTO);
    });
    expect(await screen.findByText('Contactado')).toBeInTheDocument();
  });

  it('el Dueño confirma el costo acordado en centavos', async () => {
    const confirmarMock = vi.mocked(confirmarExterno);
    confirmarMock.mockResolvedValue(EVENTO_CONFIRMADO);

    render(
      <FlujoExterno
        empleados={EXTERNOS}
        onEvento={vi.fn()}
        puedeConfirmarCosto
        turnoId={12}
      />,
    );

    await screen.findByText('Sin eventos registrados.');

    fireEvent.click(screen.getByRole('button', { name: 'Confirmar costo' }));
    fireEvent.change(screen.getByLabelText('Costo acordado'), {
      target: { value: '10.000' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }));

    await waitFor(() => {
      expect(confirmarMock).toHaveBeenCalledWith(12, 1000000);
    });
  });

  it('muestra el costo acordado cuando la API lo devuelve al Dueño', async () => {
    vi.mocked(listarEventosExterno).mockResolvedValue([EVENTO_CONFIRMADO]);

    render(
      <FlujoExterno
        empleados={EXTERNOS}
        onEvento={vi.fn()}
        puedeConfirmarCosto
        turnoId={12}
      />,
    );

    expect(await screen.findByText('$10.000,00')).toBeInTheDocument();
    expect(screen.getByText('Confirmado')).toBeInTheDocument();
  });

  it('no muestra el monto si el backend lo oculta', async () => {
    vi.mocked(listarEventosExterno).mockResolvedValue([
      {
        ...EVENTO_CONTACTO,
        tipo: 'CONFIRMADO',
        costo_acordado_centavos: null,
        costo_registrado: true,
      },
    ]);

    render(
      <FlujoExterno
        empleados={EXTERNOS}
        onEvento={vi.fn()}
        puedeConfirmarCosto={false}
        turnoId={12}
      />,
    );

    expect(
      await screen.findByText('Costo registrado (visible para el Dueño)'),
    ).toBeInTheDocument();
    expect(screen.queryByText(/\$/)).not.toBeInTheDocument();
  });

  it('muestra el error de carga y permite reintentar', async () => {
    const listarMock = vi.mocked(listarEventosExterno);
    listarMock.mockRejectedValueOnce(new Error('Sin conexión'));

    render(
      <FlujoExterno
        empleados={EXTERNOS}
        onEvento={vi.fn()}
        puedeConfirmarCosto={false}
        turnoId={12}
      />,
    );

    expect(await screen.findByText('Sin conexión')).toBeInTheDocument();

    listarMock.mockResolvedValueOnce([EVENTO_CONTACTO]);
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }));

    expect(await screen.findByText('Contactado')).toBeInTheDocument();
  });
});
