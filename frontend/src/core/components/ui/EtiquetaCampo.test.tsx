import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { Campo } from './Campo';
import { EtiquetaCampo } from './EtiquetaCampo';

describe('EtiquetaCampo', () => {
  it('marca los campos obligatorios sin ensuciar el nombre accesible', () => {
    render(
      <EtiquetaCampo htmlFor="nombre" obligatorio>
        Nombre
      </EtiquetaCampo>,
    );

    const etiqueta = screen.getByText('Nombre');

    expect(etiqueta.className).toContain('obligatorio');
    expect(etiqueta).toHaveTextContent('Nombre');
  });

  it('no marca los campos opcionales', () => {
    render(<EtiquetaCampo htmlFor="nombre">Nombre</EtiquetaCampo>);

    expect(screen.getByText('Nombre').className).not.toContain('obligatorio');
  });

  it('ubica la marca junto al texto cuando la etiqueta envuelve al control', () => {
    render(
      <EtiquetaCampo etiqueta="Fecha de inicio" htmlFor="desde" obligatorio>
        <input id="desde" />
      </EtiquetaCampo>,
    );

    expect(screen.getByText('Fecha de inicio').className).toContain(
      'obligatorio',
    );
    expect(screen.getByLabelText('Fecha de inicio')).toBeInTheDocument();
  });

  it('Campo propaga la marca de obligatorio', () => {
    render(
      <Campo etiqueta="Monto" id="monto" obligatorio>
        <input id="monto" />
      </Campo>,
    );

    expect(screen.getByText('Monto').className).toContain('obligatorio');
    expect(screen.getByLabelText('Monto')).toBeInTheDocument();
  });
});
