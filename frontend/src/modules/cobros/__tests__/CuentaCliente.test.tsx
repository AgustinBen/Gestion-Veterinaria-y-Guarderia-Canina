import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { Link, MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  listarMediosPago,
  obtenerCuentaCliente,
  obtenerPersona,
  obtenerResumenDeuda,
} from '../api';
import { CuentaCliente } from '../pages/CuentaCliente';
import type {
  CargoDetalle,
  CuentaCliente as CuentaClienteDatos,
  PersonaBusqueda,
  ResumenDeuda,
} from '../tipos';

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>();

  return {
    ...actual,
    listarMediosPago: vi.fn(),
    obtenerCuentaCliente: vi.fn(),
    obtenerPersona: vi.fn(),
    obtenerResumenDeuda: vi.fn(),
  };
});

const CARGO: CargoDetalle = {
  id: 12,
  persona_id: 3,
  paciente_id: null,
  concepto: 'Guardería día',
  total_inicial: 10000,
  origen: 'NORMAL',
  referencia_tipo: null,
  referencia_id: null,
  creado_por: 1,
  created_at: '2026-10-20T10:00:00',
  total_vigente: 10000,
  total_pagado: 2000,
  saldo: 8000,
};

function persona(id: number): PersonaBusqueda {
  return {
    id,
    nombre: `Cliente${id}`,
    apellido: 'Prueba',
    dni: null,
    dni_pendiente: false,
    telefonos: [],
  };
}

function cuenta(id: number): CuentaClienteDatos {
  return {
    persona_id: id,
    saldo_total: 8000,
    cargos: [{ cargo: { ...CARGO, persona_id: id }, pagos: [] }],
  };
}

function resumen(): ResumenDeuda {
  return {
    debe: true,
    saldo_total_centavos: 8000,
    cargos_pendientes: 1,
    deuda_mas_antigua: '2026-10-20',
    incluye_migracion: false,
  };
}

function promesaDiferida<T>() {
  let resolver: (valor: T) => void = () => undefined;
  const promesa = new Promise<T>((resolve) => {
    resolver = resolve;
  });

  return { promesa, resolver };
}

function CambiarCliente() {
  return <Link to="/cobros/cliente/4">Ir a cliente 4</Link>;
}

beforeEach(() => {
  vi.mocked(listarMediosPago).mockReset();
  vi.mocked(obtenerPersona).mockReset();
  vi.mocked(obtenerCuentaCliente).mockReset();
  vi.mocked(obtenerResumenDeuda).mockReset();

  vi.mocked(listarMediosPago).mockResolvedValue([]);
  vi.mocked(obtenerPersona).mockImplementation((id) =>
    Promise.resolve(persona(id)),
  );
  vi.mocked(obtenerCuentaCliente).mockImplementation((id) =>
    Promise.resolve(cuenta(id)),
  );
  vi.mocked(obtenerResumenDeuda).mockImplementation(() =>
    Promise.resolve(resumen()),
  );
});

describe('CuentaCliente', () => {
  it('no muestra la cuenta anterior ni sus acciones mientras carga otro cliente', async () => {
    const personaDiferida = promesaDiferida<PersonaBusqueda>();
    const cuentaDiferida = promesaDiferida<CuentaClienteDatos>();
    const resumenDiferido = promesaDiferida<ResumenDeuda>();

    vi.mocked(obtenerPersona).mockImplementation((id) =>
      id === 3 ? Promise.resolve(persona(id)) : personaDiferida.promesa,
    );
    vi.mocked(obtenerCuentaCliente).mockImplementation((id) =>
      id === 3 ? Promise.resolve(cuenta(id)) : cuentaDiferida.promesa,
    );
    vi.mocked(obtenerResumenDeuda).mockImplementation((id) =>
      id === 3 ? Promise.resolve(resumen()) : resumenDiferido.promesa,
    );

    render(
      <MemoryRouter initialEntries={['/cobros/cliente/3']}>
        <Routes>
          <Route
            element={
              <>
                <CambiarCliente />
                <CuentaCliente />
              </>
            }
            path="/cobros/cliente/:personaId"
          />
        </Routes>
      </MemoryRouter>,
    );

    expect(
      await screen.findByRole('heading', { name: 'Prueba, Cliente3' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Cobrar' })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('link', { name: 'Ir a cliente 4' }));

    expect(screen.getByRole('status')).toHaveTextContent('Cargando cuenta…');
    expect(
      screen.queryByRole('heading', { name: 'Prueba, Cliente3' }),
    ).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Cobrar' })).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: 'Ajustar precio' }),
    ).not.toBeInTheDocument();

    await act(async () => {
      personaDiferida.resolver(persona(4));
      cuentaDiferida.resolver(cuenta(4));
      resumenDiferido.resolver(resumen());
    });

    await waitFor(() =>
      expect(
        screen.getByRole('heading', { name: 'Prueba, Cliente4' }),
      ).toBeInTheDocument(),
    );
  });
});
