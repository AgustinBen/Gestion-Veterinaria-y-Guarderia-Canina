import { render, screen } from '@testing-library/react';
import { MemoryRouter, useRoutes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AuthContext, type ValorAuth } from '../../../core/auth/contexto';
import type { Rol } from '../../../core/auth/permisos';
import {
  listarIngresosPorMedio,
  listarResumen,
  obtenerDeudas,
  obtenerDetalleCliente,
} from '../api';
import { panelRoutes } from '../routes';

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>();

  return {
    ...actual,
    listarCategoriasEgreso: vi.fn().mockResolvedValue([]),
    listarEgresos: vi.fn().mockResolvedValue([]),
    listarGastosExternos: vi
      .fn()
      .mockResolvedValue({ items: [], total_centavos: 0 }),
    listarIngresosPorMedio: vi.fn(),
    listarResumen: vi.fn(),
    obtenerDeudas: vi.fn(),
    obtenerDetalleCliente: vi.fn(),
  };
});

function Rutas() {
  return useRoutes([
    ...panelRoutes,
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

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(listarResumen).mockResolvedValue({
    desde: '2026-10-01',
    hasta: '2026-10-31',
    ingresos_centavos: 0,
    ingresos_migracion_centavos: 0,
    egresos_operativos_centavos: 0,
    egresos_operativos_sin_asignar_centavos: 0,
    gastos_externos_centavos: 0,
    rentabilidad_neta_centavos: 0,
    rentabilidad_neta_motivo: null,
    calidad_datos: { cargos_otro: 0, cargos_migrados: 0, total_cargos: 0 },
  });
  vi.mocked(listarIngresosPorMedio).mockResolvedValue([]);
  vi.mocked(obtenerDeudas).mockResolvedValue({
    total_adeudado_centavos: 0,
    cantidad_clientes: 0,
    deuda_migracion_centavos: 0,
    mayores_deudores: [],
  });
  vi.mocked(obtenerDetalleCliente).mockResolvedValue({
    persona_id: 5,
    nombre: 'Ana',
    apellido: 'Paz',
    servicios: [
      {
        cargo_id: 31,
        tipo_servicio: 'GUARDERIA',
        concepto: 'Octubre',
        total_centavos: 100_000,
        pagado_centavos: 40_000,
        saldo_centavos: 60_000,
        ajustes: 0,
      },
    ],
  });
});

describe('rutas del panel y permisos', () => {
  it('el Dueño entra al tablero y a sus secciones', async () => {
    renderizar('DUENIO', '/panel');

    expect(
      await screen.findByRole('heading', { name: 'Panel' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Egresos' })).toHaveAttribute(
      'href',
      '/panel/egresos',
    );
  });

  it('el Dueño ve el detalle de un cliente', async () => {
    renderizar('DUENIO', '/panel/cliente/5');

    expect(
      await screen.findByRole('heading', { name: 'Detalle por cliente' }),
    ).toBeInTheDocument();
    expect(await screen.findByText('Paz, Ana')).toBeInTheDocument();
    expect(obtenerDetalleCliente).toHaveBeenCalledWith(5, expect.anything());
    expect(screen.getByText('$1.000,00')).toBeInTheDocument();
    expect(screen.getByText('$600,00')).toBeInTheDocument();
  });

  it('Personal no accede al panel aunque escriba la URL', () => {
    renderizar('PERSONAL', '/panel');

    expect(screen.getByText('Sin acceso')).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Panel' })).not.toBeInTheDocument();
  });

  it('Veterinario tampoco accede a las secciones del panel', () => {
    renderizar('VETERINARIO', '/panel/egresos');

    expect(screen.getByText('Sin acceso')).toBeInTheDocument();
  });

  it('sin sesión redirige al login', () => {
    render(
      <AuthContext.Provider
        value={{ sesion: null, iniciarSesion: vi.fn(), cerrarSesion: vi.fn() }}
      >
        <MemoryRouter initialEntries={['/panel']}>
          <Rutas />
        </MemoryRouter>
      </AuthContext.Provider>,
    );

    expect(screen.queryByRole('heading', { name: 'Panel' })).not.toBeInTheDocument();
  });
});
