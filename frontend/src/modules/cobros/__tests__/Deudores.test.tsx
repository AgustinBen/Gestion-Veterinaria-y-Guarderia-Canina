import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '../../../core/api/client';
import { listarDeudores } from '../api';
import { Deudores } from '../pages/Deudores';
import type { Deudor } from '../tipos';

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>();

  return {
    ...actual,
    listarDeudores: vi.fn(),
  };
});

const ANA: Deudor = {
  persona: {
    id: 3,
    nombre: 'Ana',
    apellido: 'Paz',
    telefono_principal: '1144556677',
  },
  saldo_total_centavos: 123456,
  cantidad_cargos_pendientes: 2,
  deuda_mas_antigua: '2026-03-05',
  saldo_migracion_centavos: 0,
};

const MIGRADO: Deudor = {
  persona: {
    id: 4,
    nombre: 'Luis',
    apellido: 'Gómez',
    telefono_principal: null,
  },
  saldo_total_centavos: 50000,
  cantidad_cargos_pendientes: 1,
  deuda_mas_antigua: '2025-11-10',
  saldo_migracion_centavos: 50000,
};

function renderizar() {
  return render(
    <MemoryRouter>
      <Deudores />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.mocked(listarDeudores).mockReset();
  vi.mocked(listarDeudores).mockResolvedValue([]);
});

describe('Deudores', () => {
  it('muestra cliente, saldo, cargos, fecha y enlace a la cuenta', async () => {
    vi.mocked(listarDeudores).mockResolvedValue([ANA]);
    renderizar();

    expect(await screen.findByText('Paz, Ana')).toBeInTheDocument();
    expect(screen.getByText('$1.234,56')).toBeInTheDocument();
    expect(screen.getByText('05/03/2026')).toBeInTheDocument();
    expect(screen.getByText('1144556677', { exact: false })).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: /Ver cuenta de Paz, Ana/ }),
    ).toHaveAttribute('href', '/cobros/cliente/3');
    expect(screen.queryByText('Deuda migrada')).not.toBeInTheDocument();
    expect(listarDeudores).toHaveBeenCalledWith(
      expect.objectContaining({ orden: 'monto' }),
    );
  });

  it('marca las deudas migradas', async () => {
    vi.mocked(listarDeudores).mockResolvedValue([MIGRADO]);
    renderizar();

    expect(await screen.findByText('Deuda migrada')).toBeInTheDocument();
    expect(screen.getByText('Sin teléfono registrado')).toBeInTheDocument();
  });

  it('cambia el orden y vuelve a consultar la API', async () => {
    vi.mocked(listarDeudores).mockResolvedValue([ANA]);
    renderizar();

    await screen.findByText('Paz, Ana');

    fireEvent.click(screen.getByRole('button', { name: 'Por antigüedad' }));

    await waitFor(() =>
      expect(listarDeudores).toHaveBeenLastCalledWith(
        expect.objectContaining({ orden: 'antiguedad' }),
      ),
    );
    expect(screen.getByRole('button', { name: 'Por antigüedad' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
  });

  it('carga de forma paginada los deudores posteriores al límite del backend', async () => {
    const primeraPagina = Array.from({ length: 100 }, (_, indice) => ({
      ...ANA,
      persona: {
        ...ANA.persona,
        id: indice + 1,
        nombre: `Cliente${indice + 1}`,
      },
    }));
    const siguientePagina: Deudor = {
      ...ANA,
      persona: { ...ANA.persona, id: 101, nombre: 'Cliente101' },
    };
    vi.mocked(listarDeudores)
      .mockResolvedValueOnce(primeraPagina)
      .mockResolvedValueOnce([siguientePagina]);
    renderizar();

    expect(await screen.findByText('Paz, Cliente1')).toBeInTheDocument();
    expect(listarDeudores).toHaveBeenNthCalledWith(
      1,
      expect.objectContaining({ limite: 100, offset: 0 }),
    );

    fireEvent.click(screen.getByRole('button', { name: 'Cargar más deudores' }));

    expect(await screen.findByText('Paz, Cliente101')).toBeInTheDocument();
    expect(listarDeudores).toHaveBeenNthCalledWith(
      2,
      expect.objectContaining({ limite: 100, offset: 100 }),
    );
    expect(
      screen.queryByRole('button', { name: 'Cargar más deudores' }),
    ).not.toBeInTheDocument();
  });

  it('permite reintentar la carga de la siguiente página', async () => {
    const primeraPagina = Array.from({ length: 100 }, (_, indice) => ({
      ...ANA,
      persona: {
        ...ANA.persona,
        id: indice + 1,
        nombre: `Cliente${indice + 1}`,
      },
    }));
    const siguientePagina: Deudor = {
      ...ANA,
      persona: { ...ANA.persona, id: 101, nombre: 'Cliente101' },
    };
    vi.mocked(listarDeudores)
      .mockResolvedValueOnce(primeraPagina)
      .mockRejectedValueOnce(new ApiError('No pudimos conectar.', { tipo: 'red' }))
      .mockResolvedValueOnce([siguientePagina]);
    renderizar();

    await screen.findByText('Paz, Cliente1');
    fireEvent.click(screen.getByRole('button', { name: 'Cargar más deudores' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No pudimos conectar.',
    );
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar carga' }));

    expect(await screen.findByText('Paz, Cliente101')).toBeInTheDocument();
    expect(listarDeudores).toHaveBeenNthCalledWith(
      3,
      expect.objectContaining({ limite: 100, offset: 100 }),
    );
  });

  it('avisa cuando no hay deudores', async () => {
    renderizar();

    expect(
      await screen.findByText('No hay clientes con deuda pendiente.'),
    ).toBeInTheDocument();
  });

  it('no repite la cantidad dentro de la sección: vive en el menú', async () => {
    vi.mocked(listarDeudores).mockResolvedValue([ANA, MIGRADO]);
    renderizar();

    await screen.findByText('Paz, Ana');

    const selector = screen.getByRole('group', { name: 'Ordenar deudores' });

    expect(selector.parentElement?.textContent).not.toContain('2');
  });

  it('muestra el error y permite reintentar', async () => {
    vi.mocked(listarDeudores)
      .mockRejectedValueOnce(
        new ApiError('No pudimos conectar con el servidor.', {
          tipo: 'red',
          reintentable: true,
        }),
      )
      .mockResolvedValueOnce([ANA]);
    renderizar();

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No pudimos conectar con el servidor.',
    );

    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }));

    expect(await screen.findByText('Paz, Ana')).toBeInTheDocument();
    expect(listarDeudores).toHaveBeenCalledTimes(2);
  });
});
