import { describe, expect, it, vi } from 'vitest';

import { api } from '../../core/api/client';
import { crearUsuario } from './servicioUsuarios';

describe('crearUsuario', () => {
  it('envía los datos de la cuenta al endpoint de usuarios', async () => {
    const postMock = vi.spyOn(api, 'post').mockResolvedValueOnce({
      username: 'recepcion',
      rol: 'PERSONAL',
    });

    await expect(
      crearUsuario({
        username: 'recepcion',
        password: 'clave-segura',
        rol: 'PERSONAL',
      }),
    ).resolves.toEqual({ username: 'recepcion', rol: 'PERSONAL' });

    expect(postMock).toHaveBeenCalledWith('/usuarios', {
      username: 'recepcion',
      password: 'clave-segura',
      rol: 'PERSONAL',
    });
  });
});
