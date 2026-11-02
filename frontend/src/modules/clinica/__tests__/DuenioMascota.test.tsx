import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { obtenerTitulares } from '../../padron/api';
import { DuenioMascota } from '../components/DuenioMascota';

vi.mock('../../padron/api', () => ({
  obtenerTitulares: vi.fn(),
}));

const TITULAR = {
  persona_id: 1,
  nombre: 'Marta',
  apellido: 'Gómez',
  tipo: 'TITULAR',
  principal: true,
  desde: '2026-01-01',
};

describe('DuenioMascota', () => {
  beforeEach(() => {
    vi.mocked(obtenerTitulares).mockReset();
  });

  it('muestra el titular principal para distinguir mascotas homónimas', async () => {
    vi.mocked(obtenerTitulares).mockResolvedValue([
      { ...TITULAR, persona_id: 2, nombre: 'Luis', principal: false },
      TITULAR,
    ]);

    render(<DuenioMascota pacienteId={3} />);

    expect(await screen.findByText('Marta Gómez')).toBeInTheDocument();
    expect(screen.getByText(/\(\+1\)/)).toBeInTheDocument();
    expect(obtenerTitulares).toHaveBeenCalledWith(3, expect.anything());
  });

  it('no rompe la pantalla si no se pueden leer los titulares', async () => {
    vi.mocked(obtenerTitulares).mockRejectedValue(new Error('sin señal'));

    render(<DuenioMascota pacienteId={3} />);

    expect(await screen.findByText('Dueño: sin datos')).toBeInTheDocument();
  });
});
