import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useParams } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '../../../core/api/client';
import {
  crearReserva,
  generarIdempotencyKey,
  registrarSena,
} from '../api';
import { buscarPersonas, obtenerPersona } from '../../padron/api';
import { listarMediosPago, obtenerResumenDeuda } from '../../cobros/api';
import { NuevaReserva } from '../pages/NuevaReserva';
import type { PersonaDetalle, PersonaResumen } from '../../padron/tipos';
import type { Reserva } from '../tipos';

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>();

  return {
    ...actual,
    crearReserva: vi.fn(),
    generarIdempotencyKey: vi.fn(() => 'clave-formulario'),
    registrarSena: vi.fn(),
  };
});

vi.mock('../../padron/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../padron/api')>();

  return {
    ...actual,
    buscarPersonas: vi.fn(),
    obtenerPersona: vi.fn(),
  };
});

vi.mock('../../cobros/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../cobros/api')>();

  return {
    ...actual,
    listarMediosPago: vi.fn(),
    obtenerResumenDeuda: vi.fn(),
  };
});

const TUTOR: PersonaResumen = {
  id: 8,
  nombre: 'Ana',
  apellido: 'Pérez',
  dni: '12345678',
  dni_pendiente: false,
  telefonos: [],
};

const DETALLE_TUTOR: PersonaDetalle = {
  ...TUTOR,
  domicilio: null,
  creado_en: '2026-11-01T10:00:00',
  duplicado_confirmado: false,
  mascotas: [
    {
      id: 21,
      nombre: 'Luna',
      especie_id: 1,
      especie_nombre: 'Perro',
      raza_id: null,
      raza_nombre: null,
      activo: true,
    },
    {
      id: 22,
      nombre: 'Nina',
      especie_id: 2,
      especie_nombre: 'Gato',
      raza_id: null,
      raza_nombre: null,
      activo: true,
    },
  ],
};

const RESERVA_PENDIENTE: Reserva = {
  id: 71,
  tutor_persona_id: TUTOR.id,
  desde_fecha: '2026-12-14',
  desde_franja: 'DIA',
  hasta_fecha: '2026-12-14',
  hasta_franja: 'NOCHE',
  estado: 'PENDIENTE_SENA',
  cargo_id: 51,
  total_centavos: 123456,
  sena_centavos: 0,
  pacientes: [{ paciente_id: 21, cuidados_extras: true, tipo_cuidado: null }],
  created_at: '2026-11-01T10:00:00',
};

const RESERVA_CONFIRMADA: Reserva = {
  ...RESERVA_PENDIENTE,
  estado: 'CONFIRMADA',
};

function PantallaDestino() {
  const { reservaId } = useParams();

  return <h1>Detalle de reserva {reservaId}</h1>;
}

function renderizar(ruta = '/guarderia/reservar') {
  return render(
    <MemoryRouter initialEntries={[ruta]}>
      <Routes>
        <Route element={<NuevaReserva />} path="/guarderia/reservar" />
        <Route
          element={<PantallaDestino />}
          path="/guarderia/reservas/:reservaId"
        />
      </Routes>
    </MemoryRouter>,
  );
}

async function elegirTutorYLuna() {
  fireEvent.change(screen.getByLabelText('Tutor'), {
    target: { value: 'Ana Pérez' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Buscar tutor' }));
  fireEvent.click(await screen.findByRole('button', { name: /Pérez, Ana/ }));
  fireEvent.click(await screen.findByLabelText('Luna · Perro'));
  await screen.findByLabelText('Total provisorio');
}

function completarImportes(opciones: { sena?: string } = {}) {
  fireEvent.change(screen.getByLabelText('Total provisorio'), {
    target: { value: '1.234,56' },
  });

  if (opciones.sena !== undefined) {
    fireEvent.change(screen.getByLabelText('Seña obligatoria'), {
      target: { value: opciones.sena },
    });
  }

  fireEvent.change(screen.getByLabelText('Medio de pago de la seña'), {
    target: { value: 'TRANSFERENCIA' },
  });
}

beforeEach(() => {
  vi.setSystemTime(new Date(2026, 11, 14, 12));
  vi.mocked(crearReserva).mockReset();
  vi.mocked(registrarSena).mockReset();
  vi.mocked(buscarPersonas).mockReset();
  vi.mocked(obtenerPersona).mockReset();
  vi.mocked(listarMediosPago).mockReset();
  vi.mocked(obtenerResumenDeuda).mockReset();
  vi.mocked(generarIdempotencyKey).mockReturnValue('clave-formulario');

  vi.mocked(buscarPersonas).mockResolvedValue([TUTOR]);
  vi.mocked(obtenerPersona).mockResolvedValue(DETALLE_TUTOR);
  vi.mocked(listarMediosPago).mockResolvedValue([
    {
      id: 2,
      codigo: 'TRANSFERENCIA',
      nombre: 'Transferencia',
      activo: true,
    },
  ]);
  vi.mocked(obtenerResumenDeuda).mockResolvedValue({
    debe: false,
    saldo_total_centavos: 0,
    cargos_pendientes: 0,
    deuda_mas_antigua: null,
    incluye_migracion: false,
  });
  vi.mocked(crearReserva).mockResolvedValue(RESERVA_PENDIENTE);
  vi.mocked(registrarSena).mockResolvedValue(RESERVA_CONFIRMADA);
});

describe('NuevaReserva', () => {
  it('usa la fecha del calendario al iniciar el formulario y conserva los controles nativos', async () => {
    renderizar('/guarderia/reservar?fecha=2026-12-17');
    await elegirTutorYLuna();

    expect(screen.getByLabelText('Fecha de inicio')).toHaveValue('2026-12-17');
    expect(screen.getByLabelText('Fecha de fin')).toHaveValue('2026-12-17');
    expect(screen.getByLabelText('Franja de inicio').tagName).toBe('SELECT');
    expect(screen.getByLabelText('Medio de pago de la seña').tagName).toBe(
      'SELECT',
    );
    expect(document.querySelector('[role="dialog"]')).not.toBeInTheDocument();
  });

  it('no habilita Reservar si no hay una seña positiva', async () => {
    renderizar();
    await elegirTutorYLuna();
    completarImportes();

    expect(screen.getByRole('button', { name: 'Reservar' })).toBeDisabled();
  });

  it('envía importes en centavos, mascotas y el tramo de 24 horas del mismo día', async () => {
    vi.mocked(obtenerResumenDeuda).mockResolvedValue({
      debe: true,
      saldo_total_centavos: 50000,
      cargos_pendientes: 1,
      deuda_mas_antigua: '2026-10-01',
      incluye_migracion: false,
    });
    renderizar();
    await elegirTutorYLuna();
    fireEvent.click(screen.getByRole('button', { name: '24 horas' }));
    fireEvent.click(screen.getByLabelText('Cuidados extras'));
    fireEvent.change(screen.getByLabelText('Tipo de cuidado (opcional)'), {
      target: { value: 'Administrar medicación' },
    });
    fireEvent.click(await screen.findByLabelText('Nina · Gato'));
    completarImportes({ sena: '200,50' });

    expect(await screen.findByLabelText('Deuda pendiente')).toBeInTheDocument();
    const boton = screen.getByRole('button', { name: 'Reservar' });
    expect(boton).toBeEnabled();
    fireEvent.click(boton);

    expect(await screen.findByRole('heading', { name: 'Detalle de reserva 71' }))
      .toBeInTheDocument();
    expect(crearReserva).toHaveBeenCalledWith(
      {
        tutor_persona_id: 8,
        paciente_ids: [21, 22],
        desde_fecha: '2026-12-14',
        desde_franja: 'DIA',
        hasta_fecha: '2026-12-14',
        hasta_franja: 'NOCHE',
        cuidados_extras: [
          {
            paciente_id: 21,
            cuidados_extras: true,
            tipo_cuidado: 'Administrar medicación',
          },
          { paciente_id: 22, cuidados_extras: false, tipo_cuidado: null },
        ],
        total_centavos: 123456,
      },
      { idempotencyKey: 'clave-formulario' },
    );
    expect(registrarSena).toHaveBeenCalledWith(
      71,
      { monto_centavos: 20050, medio: 'TRANSFERENCIA' },
      { idempotencyKey: 'clave-formulario' },
    );
  });

  it('ignora el doble clic mientras se crea la reserva', async () => {
    let resolver: (reserva: Reserva) => void = () => undefined;
    vi.mocked(crearReserva).mockReturnValue(
      new Promise<Reserva>((resolve) => {
        resolver = resolve;
      }),
    );
    renderizar();
    await elegirTutorYLuna();
    completarImportes({ sena: '20' });

    const boton = screen.getByRole('button', { name: 'Reservar' });
    fireEvent.click(boton);
    fireEvent.click(boton);

    expect(crearReserva).toHaveBeenCalledTimes(1);
    resolver(RESERVA_PENDIENTE);
    expect(await screen.findByRole('heading', { name: 'Detalle de reserva 71' }))
      .toBeInTheDocument();
    expect(registrarSena).toHaveBeenCalledTimes(1);
  });

  it('reutiliza la misma Idempotency-Key al reintentar un error de red', async () => {
    vi.mocked(crearReserva)
      .mockRejectedValueOnce(
        new ApiError('Sin conexión', { tipo: 'red', reintentable: true }),
      )
      .mockResolvedValueOnce(RESERVA_PENDIENTE);
    renderizar();
    await elegirTutorYLuna();
    completarImportes({ sena: '20' });
    fireEvent.click(screen.getByRole('button', { name: 'Reservar' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Sin conexión');
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar reserva' }));

    expect(await screen.findByRole('heading', { name: 'Detalle de reserva 71' }))
      .toBeInTheDocument();
    const llamadas = vi.mocked(crearReserva).mock.calls;
    expect(llamadas).toHaveLength(2);
    expect(llamadas[0]?.[1].idempotencyKey).toBe('clave-formulario');
    expect(llamadas[1]?.[1].idempotencyKey).toBe('clave-formulario');
  });

  it('reintenta la seña con la misma clave sin volver a crear la reserva', async () => {
    vi.mocked(registrarSena)
      .mockRejectedValueOnce(
        new ApiError('Sin conexión', { tipo: 'red', reintentable: true }),
      )
      .mockResolvedValueOnce(RESERVA_CONFIRMADA);
    renderizar();
    await elegirTutorYLuna();
    completarImportes({ sena: '20' });
    fireEvent.click(screen.getByRole('button', { name: 'Reservar' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Sin conexión');
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar reserva' }));

    expect(await screen.findByRole('heading', { name: 'Detalle de reserva 71' }))
      .toBeInTheDocument();
    expect(crearReserva).toHaveBeenCalledTimes(1);
    const llamadasSena = vi.mocked(registrarSena).mock.calls;
    expect(llamadasSena).toHaveLength(2);
    expect(llamadasSena[0]?.[2].idempotencyKey).toBe('clave-formulario');
    expect(llamadasSena[1]?.[2].idempotencyKey).toBe('clave-formulario');
  });

  it('muestra las fechas y franjas que devuelve la API ante SIN_CUPO', async () => {
    vi.mocked(crearReserva).mockRejectedValue(
      new ApiError('No hay lugar', {
        tipo: 'http',
        estado: 409,
        detalle: {
          codigo: 'SIN_CUPO',
          franjas_sin_lugar: [
            {
              fecha: '2026-12-15',
              franja: 'NOCHE',
              necesita: 1,
              disponible: 0,
            },
            {
              fecha: '2026-12-16',
              franja: 'DIA',
              necesita: 1,
              disponible: 0,
            },
          ],
          ocupaciones_existentes: [],
        },
      }),
    );
    renderizar();
    await elegirTutorYLuna();
    completarImportes({ sena: '20' });
    fireEvent.click(screen.getByRole('button', { name: 'Reservar' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No hay lugar el 15/12 (noche) y el 16/12 (día).',
    );
    const enlacesCalendario = screen.getAllByRole('link', { name: 'Ver calendario' });
    expect(enlacesCalendario[0]).toHaveAttribute(
      'href',
      '/guarderia/calendario',
    );
  });

  it('nombra a la mascota cuando la API responde YA_RESERVADO', async () => {
    vi.mocked(crearReserva).mockRejectedValue(
      new ApiError('Ya reservada', {
        tipo: 'http',
        estado: 409,
        detalle: {
          codigo: 'YA_RESERVADO',
          franjas_sin_lugar: [],
          ocupaciones_existentes: [
            { paciente_id: 21, fecha: '2026-12-14', franja: 'DIA' },
          ],
        },
      }),
    );
    renderizar();
    await elegirTutorYLuna();
    completarImportes({ sena: '20' });
    fireEvent.click(screen.getByRole('button', { name: 'Reservar' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Ya hay una reserva para Luna en ese tramo.',
    );
  });

  it('permite reintentar la carga de medios de pago', async () => {
    vi.mocked(listarMediosPago)
      .mockRejectedValueOnce(new Error('Sin conexión'))
      .mockResolvedValueOnce([
        {
          id: 2,
          codigo: 'TRANSFERENCIA',
          nombre: 'Transferencia',
          activo: true,
        },
      ]);
    renderizar();

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No pudimos cargar los medios de pago: Sin conexión',
    );
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }));

    await waitFor(() => expect(listarMediosPago).toHaveBeenCalledTimes(2));
  });
});
