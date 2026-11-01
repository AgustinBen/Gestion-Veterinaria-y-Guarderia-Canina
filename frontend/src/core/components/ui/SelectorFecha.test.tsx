import { useState } from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { SelectorFecha } from './SelectorFecha';

describe('SelectorFecha', () => {
  it('permite cambiar de mes y elegir una fecha en el calendario propio', async () => {
    const usuario = userEvent.setup();
    const onChange = vi.fn();
    function ControlDePrueba() {
      const [value, setValue] = useState('2024-01-15');

      return (
        <>
          <label htmlFor="fecha">Fecha aproximada</label>
          <SelectorFecha
            etiqueta="Fecha aproximada"
            id="fecha"
            onChange={(fecha) => {
              onChange(fecha);
              setValue(fecha);
            }}
            value={value}
          />
        </>
      );
    }

    render(<ControlDePrueba />);

    await usuario.click(screen.getByRole('button', { name: 'Abrir calendario: Fecha aproximada' }));
    expect(screen.getByRole('dialog', { name: 'Calendario: Fecha aproximada' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'enero de 2024' })).toBeInTheDocument();
    await usuario.click(screen.getByRole('button', { name: 'Mes siguiente' }));
    await usuario.click(screen.getByRole('button', { name: '29 de febrero de 2024' }));

    expect(onChange).toHaveBeenCalledWith('2024-02-29');
    expect(screen.getByLabelText('Fecha aproximada')).toHaveValue('29/02/2024');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('acepta fecha escrita en formato ISO y normaliza la presentación', () => {
    const onChange = vi.fn();
    render(
      <>
        <label htmlFor="fecha">Fecha aproximada</label>
        <SelectorFecha etiqueta="Fecha aproximada" id="fecha" onChange={onChange} value="" />
      </>,
    );

    fireEvent.change(screen.getByLabelText('Fecha aproximada'), {
      target: { value: '2024-06-03' },
    });

    expect(onChange).toHaveBeenCalledWith('2024-06-03');
  });
});
