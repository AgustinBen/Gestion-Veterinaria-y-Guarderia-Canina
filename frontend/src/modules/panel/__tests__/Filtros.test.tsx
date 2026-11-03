import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { Filtros } from '../components/Filtros';
import {
  calcularRango,
  fechaIsoLocal,
  leerFiltros,
  parametrosDeFiltros,
} from '../components/filtrosPanel';
import type { FiltrosPanel } from '../tipos';

const LUNES = new Date(2026, 10, 2);

const FILTROS: FiltrosPanel = {
  periodo: 'mes',
  desde: '2026-11-01',
  hasta: '2026-11-02',
};

describe('rangos de fechas del panel', () => {
  it('calcula hoy, semana, mes y mes anterior con fecha local', () => {
    expect(calcularRango('hoy', LUNES)).toEqual({
      desde: '2026-11-02',
      hasta: '2026-11-02',
    });
    expect(calcularRango('semana', LUNES)).toEqual({
      desde: '2026-11-02',
      hasta: '2026-11-02',
    });
    expect(calcularRango('mes', LUNES)).toEqual({
      desde: '2026-11-01',
      hasta: '2026-11-02',
    });
    expect(calcularRango('mes-anterior', LUNES)).toEqual({
      desde: '2026-10-01',
      hasta: '2026-10-31',
    });
  });

  it('no corre la fecha un día por la zona horaria', () => {
    expect(fechaIsoLocal(new Date(2026, 0, 1, 23, 30))).toBe('2026-01-01');
  });
});

describe('leerFiltros y parametrosDeFiltros', () => {
  it('usa el mes por defecto cuando el período no es válido', () => {
    expect(leerFiltros(new URLSearchParams('periodo=inventado'), LUNES)).toEqual({
      periodo: 'mes',
      desde: '2026-11-01',
      hasta: '2026-11-02',
    });
  });

  it('respeta las fechas de un período personalizado', () => {
    const filtros = leerFiltros(
      new URLSearchParams(
        'periodo=personalizado&desde=2026-01-05&hasta=2026-01-20',
      ),
      LUNES,
    );

    expect(filtros).toEqual({
      periodo: 'personalizado',
      desde: '2026-01-05',
      hasta: '2026-01-20',
    });
  });

  it('escribe solo período, desde y hasta en la URL', () => {
    const params = parametrosDeFiltros(FILTROS);

    expect(params.get('periodo')).toBe('mes');
    expect(params.get('desde')).toBe('2026-11-01');
    expect(params.get('hasta')).toBe('2026-11-02');
    expect(Array.from(params.keys())).toHaveLength(3);
  });
});

describe('barra de filtros', () => {
  it('avisa el período elegido y pide un rango nuevo', () => {
    const onCambiar = vi.fn();
    render(<Filtros filtros={FILTROS} onCambiar={onCambiar} />);

    expect(screen.getByRole('button', { name: 'Este mes' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );

    fireEvent.click(screen.getByRole('button', { name: 'Hoy' }));

    const esperado = calcularRango('hoy');
    expect(onCambiar).toHaveBeenCalledWith({
      periodo: 'hoy',
      desde: esperado.desde,
      hasta: esperado.hasta,
    });
  });

  it('no ofrece filtros por servicio ni por medio de pago', () => {
    render(<Filtros filtros={FILTROS} onCambiar={vi.fn()} />);

    expect(screen.queryByLabelText('Servicio')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Medio de pago')).not.toBeInTheDocument();
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
  });

  it('muestra las fechas solo en el período personalizado', () => {
    const onCambiar = vi.fn();
    const { container, rerender } = render(
      <Filtros filtros={FILTROS} onCambiar={onCambiar} />,
    );

    expect(container.querySelectorAll('input[type="date"]')).toHaveLength(0);

    rerender(
      <Filtros
        filtros={{ ...FILTROS, periodo: 'personalizado' }}
        onCambiar={onCambiar}
      />,
    );

    const fechas = container.querySelectorAll('input[type="date"]');
    expect(fechas).toHaveLength(2);

    fireEvent.change(fechas[1] as HTMLInputElement, {
      target: { value: '2026-11-15' },
    });

    expect(onCambiar).toHaveBeenCalledWith({
      periodo: 'personalizado',
      desde: '2026-11-01',
      hasta: '2026-11-15',
    });
  });
});
