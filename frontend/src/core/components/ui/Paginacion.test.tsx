import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { Paginacion } from './Paginacion';

describe('Paginacion', () => {
  it('no se muestra si hay una sola página', () => {
    const { container } = render(
      <Paginacion
        ariaLabel="Paginación de atenciones"
        cantidadPaginas={1}
        onCambiarPagina={vi.fn()}
        pagina={1}
      />,
    );

    expect(container).toBeEmptyDOMElement();
  });

  it('muestra la página actual y navega con anterior y siguiente', () => {
    const onCambiarPagina = vi.fn();

    render(
      <Paginacion
        ariaLabel="Paginación de atenciones"
        cantidadPaginas={3}
        onCambiarPagina={onCambiarPagina}
        pagina={2}
      />,
    );

    expect(
      screen.getByRole('navigation', { name: 'Paginación de atenciones' }),
    ).toBeInTheDocument();
    expect(screen.getByText('Página 2 de 3')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Página anterior' }));
    expect(onCambiarPagina).toHaveBeenLastCalledWith(1);

    fireEvent.click(screen.getByRole('button', { name: 'Página siguiente' }));
    expect(onCambiarPagina).toHaveBeenLastCalledWith(3);
  });

  it('deshabilita anterior en la primera página y siguiente en la última', () => {
    const { rerender } = render(
      <Paginacion
        ariaLabel="Paginación de atenciones"
        cantidadPaginas={2}
        onCambiarPagina={vi.fn()}
        pagina={1}
      />,
    );

    expect(screen.getByRole('button', { name: 'Página anterior' })).toBeDisabled();
    expect(
      screen.getByRole('button', { name: 'Página siguiente' }),
    ).not.toBeDisabled();

    rerender(
      <Paginacion
        ariaLabel="Paginación de atenciones"
        cantidadPaginas={2}
        onCambiarPagina={vi.fn()}
        pagina={2}
      />,
    );

    expect(
      screen.getByRole('button', { name: 'Página anterior' }),
    ).not.toBeDisabled();
    expect(screen.getByRole('button', { name: 'Página siguiente' })).toBeDisabled();
  });
});
