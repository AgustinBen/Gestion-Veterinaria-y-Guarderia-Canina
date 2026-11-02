import { describe, expect, it, vi } from 'vitest';

import { api } from '../../core/api/client';
import { crearUsuario } from './servicioUsuarios';

describe('crearUsuario', () => {
  it('envía los datos de la cuenta y del empleado al endpoint de usuarios', async () => {
    const postMock = vi.spyOn(api, 'post').mockResolvedValueOnce({
      username: 'recepcion',
      rol: 'PERSONAL',
      empleado_id: 7,
    });
    const datos = {
      username: 'recepcion',
      password: 'clave-segura',
      rol: 'PERSONAL' as const,
      empleado: {
        nombre: 'Ana',
        apellido: 'Paz',
        dni: '30111222',
        telefono: '1155550101',
      },
    };

    await expect(crearUsuario(datos)).resolves.toEqual({
      username: 'recepcion',
      rol: 'PERSONAL',
      empleado_id: 7,
    });

    expect(postMock).toHaveBeenCalledWith('/usuarios', datos);
  });
});
