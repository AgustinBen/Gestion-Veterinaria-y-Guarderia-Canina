import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '../../../core/auth/AuthContext';
import { guardarSesion } from '../../../core/auth/almacenSesion';
import {
  actualizarPaciente,
  crearPaciente,
  crearRaza,
  listarEspecies,
  listarRazas,
  listarTamanios,
  obtenerPaciente,
} from '../api';
import { AltaPaciente } from '../pages/AltaPaciente';
import type { PacienteDetalle } from '../tipos';

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>();

  return {
    ...actual,
    actualizarPaciente: vi.fn(),
    crearPaciente: vi.fn(),
    crearRaza: vi.fn(),
    listarEspecies: vi.fn(),
    listarRazas: vi.fn(),
    listarTamanios: vi.fn(),
    obtenerPaciente: vi.fn(),
  };
});

const PACIENTE: PacienteDetalle = {
  id: 8,
  nombre: 'Firulais',
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
  edad_anios: null,
  edad_meses: null,
};

function renderizar() {
  guardarSesion({ token: 'token-test', rol: 'PERSONAL', usuario: 'Prueba' });

  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={['/padron/alta-paciente?titular=5']}>
        <Routes>
          <Route path="/padron/alta-paciente" element={<AltaPaciente />} />
          <Route path="/padron/persona/:id" element={<h1>Ficha de persona</h1>} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>,
  );
}

async function elegirEspecie(usuario: ReturnType<typeof userEvent.setup>) {
  const selector = screen.getByRole('combobox', { name: 'Especie' });
  await usuario.click(selector);
  await usuario.click(await screen.findByRole('option', { name: 'Perro' }));
  await waitFor(() => expect(listarRazas).toHaveBeenCalledWith(1));
}

function formulario(container: HTMLElement): HTMLFormElement {
  const encontrado = container.querySelector('form');

  if (!encontrado) {
    throw new Error('No se encontró el formulario.');
  }

  return encontrado;
}

beforeEach(() => {
  vi.mocked(actualizarPaciente).mockReset();
  vi.mocked(crearPaciente).mockReset();
  vi.mocked(crearRaza).mockReset();
  vi.mocked(listarRazas).mockReset();
  vi.mocked(obtenerPaciente).mockReset();

  vi.mocked(listarEspecies).mockResolvedValue([
    { id: 1, nombre: 'Perro' },
    { id: 2, nombre: 'Gato' },
  ]);
  vi.mocked(listarTamanios).mockResolvedValue([{ id: 1, nombre: 'Chico' }]);
  vi.mocked(listarRazas).mockResolvedValue([]);
  vi.mocked(crearPaciente).mockResolvedValue(PACIENTE);
  vi.mocked(actualizarPaciente).mockResolvedValue(PACIENTE);
  vi.mocked(obtenerPaciente).mockResolvedValue(PACIENTE);
  vi.mocked(crearRaza).mockResolvedValue({ id: 9, nombre: 'Mestizo', especie_id: 1 });
});

describe('Alta de mascota', () => {
  it('exige la especie antes de crear', async () => {
    const usuario = userEvent.setup();
    const { container } = renderizar();

    await usuario.type(screen.getByLabelText('Nombre'), 'Firulais');
    fireEvent.submit(formulario(container));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'La especie es obligatoria.',
    );
    expect(crearPaciente).not.toHaveBeenCalled();
  });

  it('crea una raza rápida y la deja seleccionada', async () => {
    const usuario = userEvent.setup();
    renderizar();

    await usuario.type(screen.getByLabelText('Nombre'), 'Firulais');
    await elegirEspecie(usuario);
    await usuario.type(screen.getByLabelText('Nueva raza'), 'Mestizo');
    await usuario.click(screen.getByRole('button', { name: 'Crear raza' }));

    expect(crearRaza).toHaveBeenCalledWith({ nombre: 'Mestizo', especie_id: 1 });
    const selectorRaza = screen.getByRole('combobox', { name: 'Raza' });
    await waitFor(() => expect(selectorRaza).toHaveTextContent('Mestizo'));
    await usuario.click(selectorRaza);
    expect(screen.getByRole('option', { name: 'Mestizo' })).toBeInTheDocument();

    await usuario.click(screen.getByRole('button', { name: 'Guardar' }));

    expect(await screen.findByRole('heading', { name: 'Ficha de persona' })).toBeInTheDocument();
    expect(crearPaciente).toHaveBeenCalledWith(
      expect.objectContaining({
        nombre: 'Firulais',
        especie_id: 1,
        raza_id: 9,
        titular_persona_id: 5,
      }),
    );
  });

  it('calcula la edad desde la fecha y no la deja editar', async () => {
    const hoy = new Date();
    const nacimiento = new Date(hoy.getFullYear() - 2, hoy.getMonth(), 1);
    const iso = `${nacimiento.getFullYear()}-${String(nacimiento.getMonth() + 1).padStart(2, '0')}-01`;

    renderizar();

    fireEvent.change(screen.getByLabelText('Fecha de nacimiento aproximada'), {
      target: { value: iso },
    });

    const edad = screen.getByLabelText('Edad calculada');
    expect(edad.tagName).toBe('OUTPUT');
    expect(edad).toHaveTextContent('2 años');
    expect(screen.queryByRole('spinbutton', { name: 'Edad calculada' })).not.toBeInTheDocument();
  });

  it('un doble envío solo crea una mascota', async () => {
    const usuario = userEvent.setup();
    vi.mocked(crearPaciente).mockReturnValue(new Promise(() => undefined));
    const { container } = renderizar();

    await usuario.type(screen.getByLabelText('Nombre'), 'Firulais');
    await elegirEspecie(usuario);

    fireEvent.submit(formulario(container));
    fireEvent.submit(formulario(container));

    expect(crearPaciente).toHaveBeenCalledTimes(1);
  });
});
