import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '../../../core/auth/AuthContext';
import { guardarSesion } from '../../../core/auth/almacenSesion';
import type { Rol } from '../../../core/auth/permisos';
import { obtenerPaciente, obtenerPersona, obtenerTitulares } from '../api';
import { FichaPaciente } from '../pages/FichaPaciente';
import { FichaPersona } from '../pages/FichaPersona';
import type { PacienteDetalle, PersonaDetalle } from '../tipos';

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>();

  return {
    ...actual,
    obtenerPaciente: vi.fn(),
    obtenerPersona: vi.fn(),
    obtenerTitulares: vi.fn(),
  };
});

const PERSONA: PersonaDetalle = {
  id: 3,
  nombre: 'Ana',
  apellido: 'Paz',
  dni: '30111222',
  dni_pendiente: false,
  telefonos: ['1144556677'],
  domicilio: null,
  creado_en: '2026-10-01T10:00:00',
  duplicado_confirmado: false,
  mascotas: [
    {
      id: 8,
      nombre: 'Firulais',
      especie_id: 1,
      especie_nombre: 'Perro',
      raza_id: null,
      raza_nombre: null,
      activo: true,
    },
  ],
};

const PACIENTE: PacienteDetalle = {
  id: 8,
  nombre: 'Firulais',
  especie_id: 1,
  especie_nombre: 'Perro',
  raza_id: 2,
  raza_nombre: 'Mestizo',
  tamanio_id: 1,
  tamanio_nombre: 'Chico',
  peso_kg: '12.50',
  fecha_nacimiento_aprox: '2023-06-01',
  castrado: true,
  activo: true,
  edad_anios: 3,
  edad_meses: 4,
};

function renderizar(ruta: string, rol: Rol) {
  guardarSesion({ token: 'token-test', rol, usuario: 'Prueba' });

  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={[ruta]}>
        <Routes>
          <Route path="/padron/persona/:id" element={<FichaPersona />} />
          <Route path="/padron/paciente/:id" element={<FichaPaciente />} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>,
  );
}

beforeEach(() => {
  vi.mocked(obtenerPersona).mockReset();
  vi.mocked(obtenerPaciente).mockReset();
  vi.mocked(obtenerTitulares).mockReset();

  vi.mocked(obtenerPersona).mockResolvedValue(PERSONA);
  vi.mocked(obtenerPaciente).mockResolvedValue(PACIENTE);
  vi.mocked(obtenerTitulares).mockResolvedValue([
    {
      persona_id: 3,
      nombre: 'Ana',
      apellido: 'Paz',
      tipo: 'TITULAR',
      principal: true,
      desde: '2026-01-01',
    },
  ]);
});

describe('Fichas del padrón', () => {
  it('PERSONAL puede editar la persona y agregar mascotas', async () => {
    renderizar('/padron/persona/3', 'PERSONAL');

    expect(await screen.findByRole('heading', { name: 'Paz, Ana' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Editar' })).toHaveAttribute(
      'href',
      '/padron/persona/3/editar',
    );
    expect(screen.getByRole('link', { name: 'Agregar mascota' })).toHaveAttribute(
      'href',
      '/padron/alta-paciente?titular=3',
    );
  });

  it('VETERINARIO ve la ficha pero no los botones de escritura', async () => {
    renderizar('/padron/persona/3', 'VETERINARIO');

    expect(await screen.findByRole('heading', { name: 'Paz, Ana' })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Editar' })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Agregar mascota' })).not.toBeInTheDocument();
  });

  it('la ficha de mascota muestra la edad calculada y el titular principal', async () => {
    renderizar('/padron/paciente/8', 'VETERINARIO');

    expect(await screen.findByRole('heading', { name: 'Firulais' })).toBeInTheDocument();
    expect(screen.getByText('Edad calculada')).toBeInTheDocument();
    expect(screen.getByText('3 años 4 meses')).toBeInTheDocument();
    expect(screen.getByText('Paz, Ana')).toBeInTheDocument();
    expect(screen.getByText('Principal')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Ver historial de titulares' })).toHaveAttribute(
      'href',
      '/padron/paciente/8/titulares',
    );
    expect(screen.queryByRole('link', { name: 'Editar' })).not.toBeInTheDocument();
  });

  it('PERSONAL puede editar la mascota', async () => {
    renderizar('/padron/paciente/8', 'PERSONAL');

    expect(await screen.findByRole('heading', { name: 'Firulais' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Editar' })).toHaveAttribute(
      'href',
      '/padron/paciente/8/editar',
    );
  });
});
