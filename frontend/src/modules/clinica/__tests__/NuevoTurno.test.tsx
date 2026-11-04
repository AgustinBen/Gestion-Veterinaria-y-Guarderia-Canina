import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { EmpleadoDetalle, PacienteResumen } from '../../padron/tipos';
import { obtenerTitulares } from '../../padron/api';
import { crearTurno } from '../api';
import { NuevoTurno } from '../components/NuevoTurno';
import type { Turno } from '../tipos';

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>();

  return {
    ...actual,
    crearTurno: vi.fn(),
  };
});

vi.mock('../../padron/api', () => ({
  obtenerTitulares: vi.fn(),
}));

const PACIENTES: PacienteResumen[] = [
  {
    id: 4,
    nombre: 'Luna',
    especie_id: 1,
    especie_nombre: 'Perro',
    raza_id: null,
    raza_nombre: null,
    activo: true,
  },
];

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

const TURNO: Turno = {
  id: 15,
  paciente_id: 4,
  tipo: 'CONSULTA',
  veterinario_empleado_id: 7,
  inicio: '2026-11-02T09:00:00',
  fin: '2026-11-02T09:30:00',
  estado: 'PROGRAMADO',
  motivo: null,
  atencion_id: null,
  externo_actual_id: null,
  cargo_id: null,
  created_by: 1,
  created_at: '2026-10-30T10:00:00',
};

describe('NuevoTurno', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('agenda un turno con inicio y fin elegidos por el usuario', async () => {
    const crearMock = vi.mocked(crearTurno);
    crearMock.mockResolvedValue(TURNO);
    vi.mocked(obtenerTitulares).mockResolvedValue([
      {
        persona_id: 1,
        nombre: 'Marta',
        apellido: 'Paz',
        tipo: 'TITULAR',
        principal: true,
        desde: '2026-01-01',
      },
    ]);
    const onCreado = vi.fn();

    render(
      <NuevoTurno
        empleados={EMPLEADOS}
        fechaInicial="2026-11-02"
        onCreado={onCreado}
        pacientes={PACIENTES}
      />,
    );

    fireEvent.change(screen.getByLabelText('Mascota'), {
      target: { value: '4' },
    });
    fireEvent.change(screen.getByLabelText('Hora de inicio'), {
      target: { value: '09:00' },
    });
    fireEvent.change(screen.getByLabelText('Hora de fin'), {
      target: { value: '09:30' },
    });
    fireEvent.change(screen.getByLabelText('Monto a cobrar'), {
      target: { value: '10.000' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Agendar turno' }));

    await screen.findByRole('dialog');
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar y agendar' }));

    await waitFor(() => {
      expect(crearMock).toHaveBeenCalledWith(
        expect.objectContaining({
          paciente_id: 4,
          tipo: 'CONSULTA',
          veterinario_empleado_id: 7,
          inicio: '2026-11-02T09:00',
          fin: '2026-11-02T09:30',
          monto_centavos: 1000000,
        }),
      );
    });

    await waitFor(() => {
      expect(onCreado).toHaveBeenCalledWith(TURNO);
    });
  });

  function completarTurno() {
    fireEvent.change(screen.getByLabelText('Mascota'), {
      target: { value: '4' },
    });
    fireEvent.change(screen.getByLabelText('Hora de inicio'), {
      target: { value: '09:00' },
    });
    fireEvent.change(screen.getByLabelText('Hora de fin'), {
      target: { value: '09:30' },
    });
  }

  it('con monto avisa a nombre de qué dueño se carga y recién al confirmar agenda', async () => {
    const crearMock = vi.mocked(crearTurno);
    crearMock.mockResolvedValue({ ...TURNO, cargo_id: 31 });
    vi.mocked(obtenerTitulares).mockResolvedValue([
      {
        persona_id: 2,
        nombre: 'Luis',
        apellido: 'Gómez',
        tipo: 'TITULAR',
        principal: false,
        desde: '2026-01-01',
      },
      {
        persona_id: 1,
        nombre: 'Marta',
        apellido: 'Paz',
        tipo: 'TITULAR',
        principal: true,
        desde: '2026-01-01',
      },
    ]);
    const onCreado = vi.fn();

    render(
      <NuevoTurno
        empleados={EMPLEADOS}
        fechaInicial="2026-11-02"
        onCreado={onCreado}
        pacientes={PACIENTES}
      />,
    );
    completarTurno();
    fireEvent.change(screen.getByLabelText('Monto a cobrar'), {
      target: { value: '15.000,50' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Agendar turno' }));

    const dialogo = await screen.findByRole('dialog');
    expect(dialogo).toHaveTextContent(
      'Se estará cargando este pago ($15.000,50) dentro de la cuenta de Marta Paz.',
    );
    // Todavía no se agendó nada.
    expect(crearMock).not.toHaveBeenCalled();
    expect(obtenerTitulares).toHaveBeenCalledWith(4);

    fireEvent.click(screen.getByRole('button', { name: 'Confirmar y agendar' }));

    await waitFor(() => {
      expect(crearMock).toHaveBeenCalledWith(
        expect.objectContaining({ paciente_id: 4, monto_centavos: 1500050 }),
      );
    });
    await waitFor(() => expect(onCreado).toHaveBeenCalled());
  });

  it('al volver desde el aviso no agenda ni cobra', async () => {
    vi.mocked(obtenerTitulares).mockResolvedValue([
      {
        persona_id: 1,
        nombre: 'Marta',
        apellido: 'Paz',
        tipo: 'TITULAR',
        principal: true,
        desde: '2026-01-01',
      },
    ]);

    render(
      <NuevoTurno
        empleados={EMPLEADOS}
        fechaInicial="2026-11-02"
        onCreado={vi.fn()}
        pacientes={PACIENTES}
      />,
    );
    completarTurno();
    fireEvent.change(screen.getByLabelText('Monto a cobrar'), {
      target: { value: '500' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Agendar turno' }));
    await screen.findByRole('dialog');

    fireEvent.click(screen.getByRole('button', { name: 'Volver' }));

    await waitFor(() =>
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument(),
    );
    expect(crearTurno).not.toHaveBeenCalled();
  });

  it('rechaza un monto inválido sin consultar al dueño ni agendar', async () => {
    render(
      <NuevoTurno
        empleados={EMPLEADOS}
        fechaInicial="2026-11-02"
        onCreado={vi.fn()}
        pacientes={PACIENTES}
      />,
    );
    completarTurno();
    fireEvent.change(screen.getByLabelText('Monto a cobrar'), {
      target: { value: 'abc' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Agendar turno' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Monto inválido');
    expect(obtenerTitulares).not.toHaveBeenCalled();
    expect(crearTurno).not.toHaveBeenCalled();
  });

  it('exige el monto a cobrar antes de agendar', async () => {
    render(
      <NuevoTurno
        empleados={EMPLEADOS}
        fechaInicial="2026-11-02"
        onCreado={vi.fn()}
        pacientes={PACIENTES}
      />,
    );
    completarTurno();
    fireEvent.click(screen.getByRole('button', { name: 'Agendar turno' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'El monto a cobrar es obligatorio.',
    );
    expect(obtenerTitulares).not.toHaveBeenCalled();
    expect(crearTurno).not.toHaveBeenCalled();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('avisa si la mascota no tiene un dueño principal para cobrarle', async () => {
    vi.mocked(obtenerTitulares).mockResolvedValue([]);

    render(
      <NuevoTurno
        empleados={EMPLEADOS}
        fechaInicial="2026-11-02"
        onCreado={vi.fn()}
        pacientes={PACIENTES}
      />,
    );
    completarTurno();
    fireEvent.change(screen.getByLabelText('Monto a cobrar'), {
      target: { value: '500' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Agendar turno' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'La mascota no tiene un dueño principal para cobrarle.',
    );
    expect(crearTurno).not.toHaveBeenCalled();
  });

  it('al elegir Cirugía completa el veterinario externo si hay uno solo', () => {
    render(
      <NuevoTurno
        empleados={EMPLEADOS}
        fechaInicial="2026-11-02"
        onCreado={vi.fn()}
        pacientes={PACIENTES}
      />,
    );

    expect(
      screen.queryByLabelText('Veterinario externo'),
    ).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Tipo de turno'), {
      target: { value: 'CIRUGIA' },
    });

    expect(screen.getByLabelText('Veterinario externo')).toHaveValue('9');
  });

  it('con varios externos no elige ninguno por su cuenta', () => {
    const otroExterno: EmpleadoDetalle = {
      ...EMPLEADOS[1]!,
      persona_id: 10,
      nombre: 'Rita',
      apellido: 'Vega',
    };

    render(
      <NuevoTurno
        empleados={[...EMPLEADOS, otroExterno]}
        fechaInicial="2026-11-02"
        onCreado={vi.fn()}
        pacientes={PACIENTES}
      />,
    );

    fireEvent.change(screen.getByLabelText('Tipo de turno'), {
      target: { value: 'CIRUGIA' },
    });

    expect(screen.getByLabelText('Veterinario externo')).toHaveValue('');
  });

  it('rechaza un fin anterior al inicio sin llamar a la API', async () => {
    const crearMock = vi.mocked(crearTurno);

    render(
      <NuevoTurno
        empleados={EMPLEADOS}
        fechaInicial="2026-11-02"
        onCreado={vi.fn()}
        pacientes={PACIENTES}
      />,
    );

    fireEvent.change(screen.getByLabelText('Mascota'), {
      target: { value: '4' },
    });
    fireEvent.change(screen.getByLabelText('Hora de inicio'), {
      target: { value: '10:00' },
    });
    fireEvent.change(screen.getByLabelText('Hora de fin'), {
      target: { value: '09:00' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Agendar turno' }));

    expect(
      await screen.findByText('El fin del turno debe ser posterior al inicio.'),
    ).toBeInTheDocument();
    expect(crearMock).not.toHaveBeenCalled();
  });
});
