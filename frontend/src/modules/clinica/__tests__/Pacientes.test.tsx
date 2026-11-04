import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { listarPacientes, obtenerTitulares } from '../../padron/api';
import { Pacientes } from '../pages/Pacientes';

vi.mock('../../padron/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../padron/api')>();

  return {
    ...actual,
    listarPacientes: vi.fn(),
    obtenerTitulares: vi.fn(),
    buscarPacientes: vi.fn(),
  };
});

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>();

  return {
    ...actual,
    listarPacientesPorAtencion: vi.fn(),
  };
});

function paciente(id: number, nombre: string) {
  return {
    id,
    nombre,
    especie_id: 1,
    especie_nombre: 'Perro',
    raza_id: null,
    raza_nombre: null,
    activo: true,
  };
}

const PACIENTES = [
  paciente(1, 'Luna'),
  paciente(2, 'Rocky'),
  paciente(3, 'Michi'),
  paciente(4, 'Toby'),
  paciente(5, 'Nala'),
  paciente(6, 'Simba'),
  paciente(7, 'Kira'),
];

function renderizar() {
  return render(
    <MemoryRouter>
      <Pacientes />
    </MemoryRouter>,
  );
}

describe('Pacientes (historia clínica)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(listarPacientes).mockResolvedValue(PACIENTES);
    vi.mocked(obtenerTitulares).mockResolvedValue([]);
  });

  it('muestra 5 mascotas por página y permite pasar a la segunda', async () => {
    renderizar();

    expect(await screen.findByText('Luna')).toBeInTheDocument();
    expect(screen.getByText('Nala')).toBeInTheDocument();
    expect(screen.queryByText('Simba')).not.toBeInTheDocument();
    expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Página siguiente' }));

    expect(screen.getByText('Simba')).toBeInTheDocument();
    expect(screen.getByText('Kira')).toBeInTheDocument();
    expect(screen.queryByText('Luna')).not.toBeInTheDocument();
    expect(screen.getByText('Página 2 de 2')).toBeInTheDocument();
  });

  it('no muestra el paginado si hay 5 mascotas o menos', async () => {
    vi.mocked(listarPacientes).mockResolvedValue(PACIENTES.slice(0, 5));

    renderizar();

    expect(await screen.findByText('Nala')).toBeInTheDocument();
    expect(
      screen.queryByRole('navigation', { name: 'Paginación de mascotas' }),
    ).not.toBeInTheDocument();
  });
});
