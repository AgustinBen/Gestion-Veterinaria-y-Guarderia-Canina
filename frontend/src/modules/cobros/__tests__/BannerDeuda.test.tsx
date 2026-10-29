import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { BannerDeuda } from '../../../core/components/BannerDeuda';

function renderizar(props: {
  debe: boolean;
  saldoTotalCentavos: number;
  deudaMasAntigua?: string | null;
  personaId?: number;
}) {
  return render(
    <MemoryRouter>
      <BannerDeuda personaId={3} {...props} />
    </MemoryRouter>,
  );
}

describe('BannerDeuda', () => {
  it('no se muestra si no hay deuda', () => {
    const { container } = renderizar({ debe: false, saldoTotalCentavos: 0 });

    expect(container).toBeEmptyDOMElement();
  });

  it('no se muestra si el saldo no es mayor a cero', () => {
    const { container } = renderizar({ debe: true, saldoTotalCentavos: 0 });

    expect(container).toBeEmptyDOMElement();
  });

  it('avisa el saldo y desde cuándo se debe, con enlace a la cuenta', () => {
    renderizar({
      debe: true,
      saldoTotalCentavos: 123456,
      deudaMasAntigua: '2026-03-05',
    });

    const banner = screen.getByLabelText('Deuda pendiente');

    expect(banner).toHaveTextContent('Debe $1.234,56 desde 05/03');
    expect(screen.getByRole('link', { name: 'Ver cuenta' })).toHaveAttribute(
      'href',
      '/cobros/cliente/3',
    );
  });

  it('omite la fecha si no hay deuda antigua registrada', () => {
    renderizar({ debe: true, saldoTotalCentavos: 50000 });

    expect(screen.getByLabelText('Deuda pendiente')).toHaveTextContent('Debe $500,00');
    expect(screen.getByLabelText('Deuda pendiente')).not.toHaveTextContent('desde');
  });
});
