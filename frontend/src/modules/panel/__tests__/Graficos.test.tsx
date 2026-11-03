import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { GraficoDona } from '../components/GraficoDona';
import { TablaEquivalente } from '../components/TablaEquivalente';

describe('gráfico de dona', () => {
  it('dibuja la dona con CSS y conserva las etiquetas y la tabla', () => {
    const { container } = render(
      <GraficoDona
        datos={[
          { etiqueta: 'Efectivo', valor: 300_000 },
          { etiqueta: 'Débito', valor: 100_000 },
        ]}
        titulo="Ingresos por medio de pago"
      />,
    );

    expect(
      screen.getByRole('img', { name: /Efectivo: \$3\.000,00/ }),
    ).toBeInTheDocument();
    expect(container.querySelector('svg')).toBeNull();
    expect(
      screen.getByRole('list', {
        name: 'Referencias de Ingresos por medio de pago',
      }),
    ).toHaveTextContent('Débito: $1.000,00');

    const tabla = screen.getByRole('table', {
      name: 'Datos de Ingresos por medio de pago',
    });

    expect(tabla).toHaveTextContent('Efectivo');
    expect(tabla).toHaveTextContent('$3.000,00');
  });

  it('avisa cuando el total es cero', () => {
    render(
      <GraficoDona
        datos={[{ etiqueta: 'Efectivo', valor: 0 }]}
        titulo="Ingresos por servicio"
      />,
    );

    expect(screen.getByText('Sin datos para el período.')).toBeInTheDocument();
    expect(screen.queryAllByRole('img', { name: /Efectivo/ })).toHaveLength(0);
  });
});

describe('tabla equivalente', () => {
  it('muestra las filas recibidas y un mensaje cuando está vacía', () => {
    const { rerender } = render(
      <TablaEquivalente
        columnas={['Período', 'Ingresos']}
        filas={[{ etiqueta: 'Octubre', valores: ['$1.000,00'] }]}
        titulo="Serie"
      />,
    );

    const tabla = screen.getByRole('table', { name: 'Datos de Serie' });
    expect(tabla).toHaveTextContent('Octubre');
    expect(tabla).toHaveTextContent('$1.000,00');

    rerender(
      <TablaEquivalente columnas={['Período', 'Ingresos']} filas={[]} titulo="Serie" />,
    );

    expect(screen.getByRole('table', { name: 'Datos de Serie' })).toHaveTextContent(
      'Sin datos para el período.',
    );
  });
});
