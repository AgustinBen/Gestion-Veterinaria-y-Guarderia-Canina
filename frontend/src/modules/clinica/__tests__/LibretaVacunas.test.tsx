import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { LibretaVacunas } from '../components/LibretaVacunas';
import type { LibretaVacunasItem } from '../tipos';

const VACUNAS: LibretaVacunasItem[] = [
  {
    atencion_id: 1,
    nombre_vacuna: 'Quíntuple',
    lote: 'LOTE-A',
    fecha_aplicacion: '2026-01-10',
    proxima_dosis: '2027-01-10',
    estado: 'VIGENTE',
  },
  {
    atencion_id: 2,
    nombre_vacuna: 'Antirrábica',
    lote: null,
    fecha_aplicacion: '2024-05-01',
    proxima_dosis: null,
    estado: 'VENCIDA',
  },
];

describe('LibretaVacunas', () => {
  it('muestra las vacunas con lote, fechas y estado', () => {
    render(<LibretaVacunas items={VACUNAS} />);

    expect(
      screen.getByRole('heading', { name: 'Libreta de vacunas' }),
    ).toBeInTheDocument();
    expect(screen.getByText('Quíntuple')).toBeInTheDocument();
    expect(screen.getByText('LOTE-A')).toBeInTheDocument();
    expect(screen.getByText('Vigente')).toBeInTheDocument();
    expect(screen.getByText('Antirrábica')).toBeInTheDocument();
    expect(screen.getByText('Vencida')).toBeInTheDocument();
    expect(screen.getByText('2027-01-10')).toBeInTheDocument();
    expect(screen.getByText('2 aplicadas')).toBeInTheDocument();
  });

  it('avisa cuando todavía no hay vacunas', () => {
    render(<LibretaVacunas items={[]} />);

    expect(
      screen.getByText(
        'Todavía no hay vacunas registradas para esta mascota.',
      ),
    ).toBeInTheDocument();
    expect(screen.getByText('0 aplicadas')).toBeInTheDocument();
  });
});
