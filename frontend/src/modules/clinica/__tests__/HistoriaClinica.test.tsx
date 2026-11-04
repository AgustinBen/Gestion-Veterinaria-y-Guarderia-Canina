import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AuthContext, type ValorAuth } from '../../../core/auth/contexto';
import { listarEmpleados, obtenerPaciente, obtenerTitulares } from '../../padron/api';
import { listarAtenciones, listarEstudios, obtenerLibreta } from '../api';
import { HistoriaClinica } from '../pages/HistoriaClinica';
import type { AtencionResumen } from '../tipos';

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>();

  return {
    ...actual,
    listarAtenciones: vi.fn(),
    listarEstudios: vi.fn(),
    obtenerLibreta: vi.fn(),
  };
});

vi.mock('../../padron/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../padron/api')>();

  return {
    ...actual,
    listarEmpleados: vi.fn(),
    obtenerPaciente: vi.fn(),
    obtenerTitulares: vi.fn(),
  };
});

const PACIENTE = {
  id: 3,
  nombre: 'Luna',
  especie_id: 1,
  especie_nombre: 'Perro',
  raza_id: null,
  raza_nombre: null,
  tamanio_id: null,
  tamanio_nombre: null,
  peso_kg: null,
  fecha_nacimiento_aprox: null,
  castrado: null,
  activo: true,
  edad_anios: 3,
  edad_meses: 0,
};

function atencion(id: number): AtencionResumen {
  return {
    id,
    paciente_id: 3,
    tipo: 'CONSULTA',
    fecha_hora: `2026-11-0${((id - 1) % 9) + 1}T10:00:00`,
    veterinario_empleado_id: 7,
    veterinario_nombre: 'Dra. Paz',
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
  };
}

const valorAuth: ValorAuth = {
  sesion: { token: 'token-prueba', rol: 'DUENIO', usuario: 'prueba' },
  iniciarSesion: vi.fn(),
  cerrarSesion: vi.fn(),
};

function renderizar() {
  return render(
    <AuthContext.Provider value={valorAuth}>
      <MemoryRouter initialEntries={['/historia-clinica/3']}>
        <Routes>
          <Route path="/historia-clinica/:pacienteId" element={<HistoriaClinica />} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
}

describe('HistoriaClinica', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(obtenerPaciente).mockResolvedValue(PACIENTE);
    vi.mocked(listarEmpleados).mockResolvedValue([]);
    vi.mocked(obtenerTitulares).mockResolvedValue([]);
    vi.mocked(listarEstudios).mockResolvedValue([]);
    vi.mocked(obtenerLibreta).mockResolvedValue([]);
    vi.mocked(listarAtenciones).mockResolvedValue(
      [1, 2, 3, 4, 5, 6, 7].map(atencion),
    );
  });

  it('muestra 5 atenciones por página y permite pasar a la segunda', async () => {
    renderizar();

    expect(await screen.findByText('Consulta · #1')).toBeInTheDocument();
    expect(screen.getByText('Consulta · #5')).toBeInTheDocument();
    expect(screen.queryByText('Consulta · #6')).not.toBeInTheDocument();
    expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Página siguiente' }));

    expect(screen.getByText('Consulta · #6')).toBeInTheDocument();
    expect(screen.getByText('Consulta · #7')).toBeInTheDocument();
    expect(screen.queryByText('Consulta · #1')).not.toBeInTheDocument();
    expect(screen.getByText('Página 2 de 2')).toBeInTheDocument();
  });

  it('vuelve a la primera página al cambiar de filtro', async () => {
    renderizar();

    expect(await screen.findByText('Consulta · #1')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Página siguiente' }));
    expect(screen.getByText('Página 2 de 2')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Consultas' }));

    expect(screen.getByText('Consulta · #1')).toBeInTheDocument();
    expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
  });
});
