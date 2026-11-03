import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '../../../core/api/client';
import {
  listarIngresosPorMedio,
  listarResumen,
  obtenerDeudas,
} from '../api';
import { fechaIsoLocal } from '../components/filtrosPanel';
import { Tablero } from '../pages/Tablero';
import type { DeudasPanel, ResumenPanel } from '../tipos';

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>();

  return {
    ...actual,
    listarIngresosPorMedio: vi.fn(),
    listarResumen: vi.fn(),
    obtenerDeudas: vi.fn(),
  };
});

const RESUMEN: ResumenPanel = {
  desde: '2026-10-01',
  hasta: '2026-10-31',
  ingresos_centavos: 150_000,
  ingresos_migracion_centavos: 0,
  egresos_operativos_centavos: 50_000,
  egresos_operativos_sin_asignar_centavos: 0,
  gastos_externos_centavos: 20_000,
  rentabilidad_neta_centavos: 80_000,
  rentabilidad_neta_motivo: null,
  calidad_datos: { cargos_otro: 0, cargos_migrados: 0, total_cargos: 3 },
};

const DEUDAS: DeudasPanel = {
  total_adeudado_centavos: 70_000,
  cantidad_clientes: 2,
  deuda_migracion_centavos: 0,
  mayores_deudores: [],
};

function renderizar(ruta = '/panel') {
  return render(
    <MemoryRouter initialEntries={[ruta]}>
      <Tablero />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(listarResumen).mockResolvedValue(RESUMEN);
  vi.mocked(listarIngresosPorMedio).mockResolvedValue([
    { medio: 'EFECTIVO', ingresos_centavos: 150_000 },
  ]);
  vi.mocked(obtenerDeudas).mockResolvedValue(DEUDAS);
});

describe('Tablero del panel', () => {
  it('muestra las cuatro métricas y el total de deudas sin listar deudores', async () => {
    renderizar();

    expect(
      await screen.findByRole('heading', { name: 'Panel' }),
    ).toBeInTheDocument();

    expect(screen.getByRole('region', { name: 'Ingresos' })).toHaveTextContent(
      '$1.500,00',
    );
    expect(
      screen.getByRole('region', { name: 'Egresos operativos' }),
    ).toHaveTextContent('$500,00');
    expect(
      screen.getByRole('region', { name: 'Gastos a externos' }),
    ).toHaveTextContent('$200,00');
    expect(
      screen.getByRole('region', { name: 'Rentabilidad neta' }),
    ).toHaveTextContent('$800,00');

    const deudas = screen.getByRole('region', { name: 'Deudas pendientes' });
    expect(deudas).toHaveTextContent('$700,00');
    expect(deudas).toHaveTextContent('2 cliente(s) con deuda.');
    expect(deudas).toHaveTextContent(
      'El saldo adeudado no se descuenta de la rentabilidad.',
    );
    expect(
      within(deudas).getByRole('link', { name: 'Ver deudores' }),
    ).toHaveAttribute('href', '/cobros/deudores');
  });

  it('no repite la búsqueda de clientes ni el detalle por cliente', async () => {
    renderizar();

    await screen.findByRole('region', { name: 'Ingresos' });

    expect(
      screen.queryByRole('heading', { name: 'Detalle por cliente' }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole('textbox', { name: 'Buscar cliente' }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole('link', { name: /Paz, Ana/ }),
    ).not.toBeInTheDocument();
  });

  it('muestra solo el gráfico de dona de ingresos por medio de pago', async () => {
    renderizar();

    await screen.findByRole('region', {
      name: 'Gráfico de ingresos por medio de pago',
    });

    expect(
      screen.getByRole('img', { name: /^Ingresos por medio de pago/ }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole('img', { name: 'Ingresos por servicio' }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole('img', { name: 'Ingresos contra egresos' }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText('Ingresos por servicio'),
    ).not.toBeInTheDocument();
  });

  it('explica por qué falta la rentabilidad en vez de mostrar un cero', async () => {
    vi.mocked(listarResumen).mockResolvedValue({
      ...RESUMEN,
      rentabilidad_neta_centavos: null,
      rentabilidad_neta_motivo: 'Hay egresos sin categoría asignada.',
    });
    renderizar();

    const rentabilidad = await screen.findByRole('region', {
      name: 'Rentabilidad neta',
    });

    expect(rentabilidad).toHaveTextContent('—');
    expect(rentabilidad).toHaveTextContent(
      'Hay egresos sin categoría asignada.',
    );
  });

  it('avisa cuando no hay deudas pendientes', async () => {
    vi.mocked(obtenerDeudas).mockResolvedValue({
      ...DEUDAS,
      total_adeudado_centavos: 0,
      cantidad_clientes: 0,
    });
    renderizar();

    expect(
      await screen.findByText('No hay deudas pendientes.'),
    ).toBeInTheDocument();
  });

  it('avisa cuando no hay datos para el gráfico', async () => {
    vi.mocked(listarIngresosPorMedio).mockResolvedValue([]);
    renderizar();

    await screen.findByRole('region', {
      name: 'Gráfico de ingresos por medio de pago',
    });

    expect(screen.getAllByText('Sin datos para el período.')).toHaveLength(2);
  });

  it('muestra el error y permite reintentar', async () => {
    vi.mocked(listarResumen)
      .mockRejectedValueOnce(
        new ApiError('No pudimos conectar con el servidor.', {
          tipo: 'red',
          reintentable: true,
        }),
      )
      .mockResolvedValue(RESUMEN);
    renderizar();

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No pudimos conectar con el servidor.',
    );

    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }));

    expect(
      await screen.findByRole('region', { name: 'Ingresos' }),
    ).toHaveTextContent('$1.500,00');
    expect(listarResumen).toHaveBeenCalledTimes(2);
  });

  it('vuelve a consultar cuando cambia el período', async () => {
    renderizar();

    await screen.findByRole('region', { name: 'Ingresos' });

    fireEvent.click(screen.getByRole('button', { name: 'Hoy' }));

    const hoy = fechaIsoLocal(new Date());
    await waitFor(() =>
      expect(listarResumen).toHaveBeenLastCalledWith(
        expect.objectContaining({ desde: hoy, hasta: hoy }),
        expect.anything(),
      ),
    );
  });
});
