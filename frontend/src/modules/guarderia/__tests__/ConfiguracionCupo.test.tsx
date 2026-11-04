import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  actualizarConfiguracionCupo,
  obtenerConfiguracionCupo,
} from '../api';
import { ConfiguracionCupo } from '../pages/ConfiguracionCupo';
import type { ConfiguracionCupo as ConfiguracionCupoTipo } from '../tipos';

vi.mock('../api', () => ({
  actualizarConfiguracionCupo: vi.fn(),
  mensajeDeError: (error: unknown) =>
    error instanceof Error ? error.message : 'Error desconocido',
  obtenerConfiguracionCupo: vi.fn(),
}));

const CONFIGURACION: ConfiguracionCupoTipo = {
  cupo_maximo: 4,
  cupo_minimo: 2,
  cupo_maximo_permitido: 4,
  fecha_consultada: null,
  cupo_fecha: null,
  fecha_es_excepcion: false,
  sobreocupaciones: [],
};

function renderizar(ruta = '/') {
  return render(
    <MemoryRouter initialEntries={[ruta]}>
      <ConfiguracionCupo />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.mocked(obtenerConfiguracionCupo).mockReset().mockResolvedValue(CONFIGURACION);
  vi.mocked(actualizarConfiguracionCupo).mockReset().mockResolvedValue({
    ...CONFIGURACION,
    cupo_maximo: 2,
    sobreocupaciones: [
      {
        fecha: '2026-11-04',
        franja: 'DIA',
        publico: 1,
        ocupado: 3,
        exceso: 2,
      },
    ],
  });
});

describe('Configuración del cupo de guardería', () => {
  it('guarda el cupo y advierte el exceso sin sugerir cancelar reservas', async () => {
    vi.mocked(obtenerConfiguracionCupo)
      .mockReset()
      .mockResolvedValueOnce(CONFIGURACION)
      .mockResolvedValueOnce({
        ...CONFIGURACION,
        sobreocupaciones: [
          {
            fecha: '2026-11-04',
            franja: 'DIA',
            publico: 1,
            ocupado: 3,
            exceso: 2,
          },
        ],
      });
    renderizar();

    const campo = await screen.findByLabelText(
      'Cupo máximo general por fecha y franja',
    );
    expect(campo).toHaveAttribute('min', '2');
    expect(campo).toHaveAttribute('max', '4');
    fireEvent.change(campo, { target: { value: '2' } });
    fireEvent.click(screen.getByRole('button', { name: 'Guardar cupo' }));

    await waitFor(() =>
      expect(actualizarConfiguracionCupo).toHaveBeenCalledWith(2),
    );
    expect(await screen.findByRole('heading', { name: 'Reservas existentes por encima del cupo' })).toBeInTheDocument();
    expect(screen.getByText(/disponibilidad para nuevas reservas es cero/)).toBeInTheDocument();
    expect(screen.getByText(/exceso de 2/)).toBeInTheDocument();
  });

  it('guarda una excepción para la fecha seleccionada', async () => {
    const fecha = '2026-12-14';
    vi.mocked(obtenerConfiguracionCupo)
      .mockReset()
      .mockResolvedValue({
        ...CONFIGURACION,
        fecha_consultada: fecha,
        cupo_fecha: 4,
      });
    renderizar(`/guarderia/configuracion?fecha=${fecha}`);

    expect(await screen.findByLabelText('Fecha individual')).toHaveValue(fecha);
    const campo = screen.getByLabelText('Cupo máximo para esta fecha y franja');
    fireEvent.change(campo, { target: { value: '3' } });
    fireEvent.click(
      screen.getByRole('button', { name: 'Guardar cupo de esta fecha' }),
    );

    await waitFor(() =>
      expect(actualizarConfiguracionCupo).toHaveBeenCalledWith(3, fecha),
    );
  });

  it('muestra errores de carga y permite reintentar', async () => {
    vi.mocked(obtenerConfiguracionCupo)
      .mockReset()
      .mockRejectedValueOnce(new Error('Servicio no disponible'))
      .mockResolvedValueOnce(CONFIGURACION);

    renderizar();

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No pudimos cargar la configuración: Servicio no disponible',
    );
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }));

    expect(
      await screen.findByLabelText('Cupo máximo general por fecha y franja'),
    ).toHaveValue(4);
  });
});
