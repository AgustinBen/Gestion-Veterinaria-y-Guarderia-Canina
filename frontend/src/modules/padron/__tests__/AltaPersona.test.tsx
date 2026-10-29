import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '../../../core/api/client';
import { AuthProvider } from '../../../core/auth/AuthContext';
import { guardarSesion } from '../../../core/auth/almacenSesion';
import { crearPersona } from '../api';
import { AltaPersona } from '../pages/AltaPersona';
import type { PersonaDetalle, PersonaResumen } from '../tipos';

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>();

  return {
    ...actual,
    crearPersona: vi.fn(),
    actualizarPersona: vi.fn(),
    obtenerPersona: vi.fn(),
  };
});

const EXISTENTE: PersonaResumen = {
  id: 7,
  nombre: 'Ana',
  apellido: 'Paz',
  dni: '30111222',
  dni_pendiente: false,
  telefonos: ['1144556677'],
};

const CREADA: PersonaDetalle = {
  ...EXISTENTE,
  id: 12,
  domicilio: null,
  creado_en: '2026-10-27T10:00:00',
  duplicado_confirmado: true,
  mascotas: [],
};

function renderizar() {
  guardarSesion({ token: 'token-test', rol: 'PERSONAL', usuario: 'Prueba' });

  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={['/padron/alta-persona']}>
        <Routes>
          <Route path="/padron" element={<h1>Listado de personas</h1>} />
          <Route path="/padron/alta-persona" element={<AltaPersona />} />
          <Route path="/padron/persona/:id" element={<h1>Ficha de persona</h1>} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>,
  );
}

async function completarFormulario(usuario: ReturnType<typeof userEvent.setup>) {
  await usuario.type(screen.getByLabelText('Nombre'), 'Ana');
  await usuario.type(screen.getByLabelText('Apellido'), 'Paz');
  await usuario.type(screen.getByLabelText('DNI'), '30111222');
  await usuario.type(screen.getByLabelText('Teléfonos'), '1144556677');
}

function errorPosibleDuplicado() {
  return new ApiError('Hay coincidencias.', {
    tipo: 'http',
    estado: 409,
    detalle: {
      codigo: 'POSIBLE_DUPLICADO',
      coincidencias: [
        {
          persona: EXISTENTE,
          motivo: 'Teléfono repetido',
          mascotas: ['Firulais'],
        },
      ],
    },
  });
}

beforeEach(() => {
  vi.mocked(crearPersona).mockReset();
});

describe('Alta de dueño', () => {
  it('un DNI repetido bloquea el alta sin pedir confirmación', async () => {
    const usuario = userEvent.setup();
    vi.mocked(crearPersona).mockRejectedValue(
      new ApiError('DNI repetido.', {
        tipo: 'http',
        estado: 409,
        detalle: { codigo: 'DNI_DUPLICADO', persona: EXISTENTE },
      }),
    );
    renderizar();

    await completarFormulario(usuario);
    await usuario.click(screen.getByRole('button', { name: 'Guardar' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Ya existe una persona con ese DNI. No se puede crear otra.',
    );
    expect(screen.getByRole('link', { name: 'Ver ficha existente' })).toHaveAttribute(
      'href',
      '/padron/persona/7',
    );
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(crearPersona).toHaveBeenCalledTimes(1);
  });

  it('un posible duplicado abre el modal y no crea nada', async () => {
    const usuario = userEvent.setup();
    vi.mocked(crearPersona).mockRejectedValue(errorPosibleDuplicado());
    renderizar();

    await completarFormulario(usuario);
    await usuario.click(screen.getByRole('button', { name: 'Guardar' }));

    expect(await screen.findByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText(/Teléfono repetido/)).toBeInTheDocument();
    expect(crearPersona).toHaveBeenCalledTimes(1);
  });

  it('si es la misma persona navega a su ficha sin crear otra', async () => {
    const usuario = userEvent.setup();
    vi.mocked(crearPersona).mockRejectedValue(errorPosibleDuplicado());
    renderizar();

    await completarFormulario(usuario);
    await usuario.click(screen.getByRole('button', { name: 'Guardar' }));
    await usuario.click(
      screen.getByRole('button', { name: 'Es la misma persona (abrir su ficha)' }),
    );

    expect(await screen.findByRole('heading', { name: 'Ficha de persona' })).toBeInTheDocument();
    expect(crearPersona).toHaveBeenCalledTimes(1);
  });

  it('confirma el duplicado y reenvía con confirmar_duplicado', async () => {
    const usuario = userEvent.setup();
    vi.mocked(crearPersona)
      .mockRejectedValueOnce(errorPosibleDuplicado())
      .mockResolvedValueOnce(CREADA);
    renderizar();

    await completarFormulario(usuario);
    await usuario.click(screen.getByRole('button', { name: 'Guardar' }));
    await usuario.click(screen.getByRole('button', { name: 'Es otra persona, crear igual' }));
    await usuario.click(screen.getByRole('button', { name: 'Confirmar y crear' }));

    expect(
      await screen.findByRole('heading', { name: 'Listado de personas' }),
    ).toBeInTheDocument();
    expect(crearPersona).toHaveBeenCalledTimes(2);
    expect(crearPersona).toHaveBeenLastCalledWith(
      expect.objectContaining({
        dni: '30111222',
        confirmar_duplicado: true,
      }),
    );
  });

  it('un doble envío solo crea una persona', async () => {
    const usuario = userEvent.setup();
    vi.mocked(crearPersona).mockReturnValue(new Promise(() => undefined));
    const { container } = renderizar();

    await completarFormulario(usuario);
    const formulario = container.querySelector('form');

    if (!formulario) {
      throw new Error('No se encontró el formulario.');
    }

    fireEvent.submit(formulario);
    fireEvent.submit(formulario);

    expect(crearPersona).toHaveBeenCalledTimes(1);
  });
});
