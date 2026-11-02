import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, useRoutes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AuthContext, type ValorAuth } from '../../../core/auth/contexto';
import type { Rol } from '../../../core/auth/permisos';
import { listarEmpleados, listarPacientes } from '../../padron/api';
import type { EmpleadoDetalle } from '../../padron/tipos';
import { listarIdsVeterinarios } from '../api';
import { clinicaRoutes } from '../routes';

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>();

  return {
    ...actual,
    listarAtenciones: vi.fn().mockResolvedValue([]),
    listarEstudios: vi.fn().mockResolvedValue([]),
    listarIdsVeterinarios: vi.fn().mockResolvedValue([]),
    obtenerAgenda: vi.fn().mockResolvedValue([]),
    obtenerLibreta: vi.fn().mockResolvedValue([]),
  };
});

vi.mock('../../padron/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../padron/api')>();

  return {
    ...actual,
    listarEmpleados: vi.fn().mockResolvedValue([]),
    listarPacientes: vi.fn().mockResolvedValue([]),
    obtenerPaciente: vi.fn().mockResolvedValue({
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
    }),
  };
});

function Rutas() {
  return useRoutes([
    ...clinicaRoutes,
    { path: '/sin-acceso', element: <p>Sin acceso</p> },
  ]);
}

function valorAuth(rol: Rol): ValorAuth {
  return {
    sesion: { token: 'token-prueba', rol, usuario: 'prueba' },
    iniciarSesion: vi.fn(),
    cerrarSesion: vi.fn(),
  };
}

function renderizar(rol: Rol, ruta: string) {
  return render(
    <AuthContext.Provider value={valorAuth(rol)}>
      <MemoryRouter initialEntries={[ruta]}>
        <Rutas />
      </MemoryRouter>
    </AuthContext.Provider>,
  );
}

describe('rutas de clínica y permisos', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(listarEmpleados).mockResolvedValue([]);
    vi.mocked(listarPacientes).mockResolvedValue([]);
    vi.mocked(listarIdsVeterinarios).mockResolvedValue([]);
  });

  it('PERSONAL no puede abrir la historia clínica', async () => {
    renderizar('PERSONAL', '/historia-clinica');

    expect(await screen.findByText('Sin acceso')).toBeInTheDocument();
    expect(
      screen.queryByRole('heading', { name: 'Historia clínica' }),
    ).not.toBeInTheDocument();
  });

  it('VETERINARIO puede abrir la ficha de una mascota y registrar atenciones', async () => {
    renderizar('VETERINARIO', '/historia-clinica/3');

    expect(
      await screen.findByRole('heading', { name: 'Luna' }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Registrar atención' }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'Libreta de vacunas' }),
    ).toBeInTheDocument();
    expect(
      await screen.findByText('Todavía no hay atenciones registradas.'),
    ).toBeInTheDocument();
  });

  it('PERSONAL ve la agenda y puede agendar, sin sección de turnos del personal', async () => {
    renderizar('PERSONAL', '/turnos');

    expect(
      await screen.findByRole('heading', { name: 'Turnos' }),
    ).toBeInTheDocument();
    expect(
      await screen.findByText('No hay turnos el día de hoy.'),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Nuevo turno' })).toBeInTheDocument();
    expect(screen.getByLabelText('Veterinario')).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: 'Asignar turno' }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText(/turnos del personal/i)).not.toBeInTheDocument();
  });

  it('VETERINARIO ve sus turnos pero no puede agendar ni elegir otro veterinario', async () => {
    renderizar('VETERINARIO', '/turnos');

    expect(
      await screen.findByRole('heading', { name: 'Turnos' }),
    ).toBeInTheDocument();
    expect(screen.getByText('Tus turnos asignados.')).toBeInTheDocument();
    expect(
      screen.queryByRole('link', { name: 'Nuevo turno' }),
    ).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Veterinario')).not.toBeInTheDocument();
  });

  it('VETERINARIO no puede abrir la pantalla de nuevo turno por URL', async () => {
    renderizar('VETERINARIO', '/turnos/nueva');

    expect(await screen.findByText('Sin acceso')).toBeInTheDocument();
    expect(
      screen.queryByRole('heading', { name: 'Nuevo turno' }),
    ).not.toBeInTheDocument();
  });

  it('informa cuando no hay turnos en la semana', async () => {
    renderizar('PERSONAL', '/turnos');
    fireEvent.click(await screen.findByRole('button', { name: 'Semana' }));

    expect(
      await screen.findByText('No hay turnos en la semana.'),
    ).toBeInTheDocument();
  });

  it('DUENIO puede agendar turnos', async () => {
    renderizar('DUENIO', '/turnos');

    expect(
      await screen.findByRole('heading', { name: 'Turnos' }),
    ).toBeInTheDocument();
    expect(
      await screen.findByRole('link', { name: 'Nuevo turno' }),
    ).toBeInTheDocument();
  });

  it('PERSONAL puede crear turnos veterinarios', async () => {
    renderizar('PERSONAL', '/turnos/nueva');

    expect(
      await screen.findByRole('heading', { name: 'Nuevo turno' }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Agendar turno' }),
    ).toBeInTheDocument();
  });

  it('el selector de turno solo ofrece empleados con usuario veterinario', async () => {
    const empleados: EmpleadoDetalle[] = [
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
        tipo: 'INTERNO',
        es_veterinario: true,
        especialidad: null,
        email: null,
        activo: true,
      },
    ];
    vi.mocked(listarEmpleados).mockResolvedValue(empleados);
    vi.mocked(listarIdsVeterinarios).mockResolvedValue([7]);

    renderizar('PERSONAL', '/turnos/nueva');

    const selector = await screen.findByLabelText('Veterinario');
    expect(selector).toHaveValue('7');
    expect(screen.getByRole('option', { name: 'Ana Paz' })).toBeInTheDocument();
    expect(
      screen.queryByRole('option', { name: 'Mario Sosa' }),
    ).not.toBeInTheDocument();
  });
});
