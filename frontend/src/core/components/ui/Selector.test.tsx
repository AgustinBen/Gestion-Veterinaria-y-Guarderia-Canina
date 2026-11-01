import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { Selector } from './Selector';

const OPCIONES = [
  { value: 'perro', label: 'Perro' },
  { value: 'gato', label: 'Gato' },
  { value: 'pez', label: 'Pez', disabled: true },
];

function renderizar(onChange = vi.fn()) {
  render(
    <>
      <label htmlFor="especie">Especie</label>
      <Selector
        id="especie"
        onChange={onChange}
        opciones={OPCIONES}
        placeholder="Seleccionar especie"
        value=""
      />
    </>,
  );

  return onChange;
}

describe('Selector', () => {
  it('muestra y elige una opción con el menú personalizado', async () => {
    const usuario = userEvent.setup();
    const onChange = renderizar();
    const control = screen.getByRole('combobox', { name: 'Especie' });

    await usuario.click(control);
    expect(screen.queryByRole('option', { name: 'Seleccionar especie' })).not.toBeInTheDocument();
    await usuario.click(screen.getByRole('option', { name: 'Gato' }));

    expect(onChange).toHaveBeenCalledWith('gato');
    expect(control).toHaveAttribute('aria-expanded', 'false');
  });

  it('permite recorrer las opciones con el teclado y omite las deshabilitadas', () => {
    const onChange = renderizar();
    const control = screen.getByRole('combobox', { name: 'Especie' });

    fireEvent.keyDown(control, { key: 'ArrowDown' });
    expect(control).toHaveAttribute('aria-expanded', 'true');
    fireEvent.keyDown(control, { key: 'Enter' });

    expect(onChange).toHaveBeenCalledWith('perro');
    expect(onChange).not.toHaveBeenCalledWith('pez');
  });

  it('no permite seleccionar opciones deshabilitadas', async () => {
    const usuario = userEvent.setup();
    const onChange = renderizar();

    await usuario.click(screen.getByRole('combobox', { name: 'Especie' }));
    await usuario.click(screen.getByRole('option', { name: 'Pez' }));

    expect(onChange).not.toHaveBeenCalled();
  });
});
