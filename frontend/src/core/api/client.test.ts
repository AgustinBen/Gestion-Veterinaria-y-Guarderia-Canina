import { describe, expect, it, vi } from 'vitest';

import { ApiError, crearCliente, type OpcionesCliente } from './client';

function respuestaJson(datos: unknown, estado = 200): Response {
  return new Response(JSON.stringify(datos), {
    status: estado,
    headers: { 'Content-Type': 'application/json' },
  });
}

function crearClientePrueba(opciones: OpcionesCliente = {}) {
  const fetchFalso = vi.fn<typeof fetch>();

  const cliente = crearCliente({
    baseUrl: 'http://api.local',
    getToken: () => 'token-prueba',
    onNoAutorizado: () => undefined,
    fetch: fetchFalso,
    ...opciones,
  });

  function llamada(indice = 0): [RequestInfo | URL, RequestInit] {
    const registrada = fetchFalso.mock.calls[indice];

    if (!registrada) {
      throw new Error(`No se registró la llamada ${indice}.`);
    }

    return [registrada[0], registrada[1] ?? {}];
  }

  function cabeceras(indice = 0): Headers {
    return new Headers(llamada(indice)[1].headers);
  }

  return { cliente, fetchFalso, llamada, cabeceras };
}

describe('ClienteApi', () => {
  it('envía el token en cada solicitud', async () => {
    const { cliente, fetchFalso, cabeceras } = crearClientePrueba();

    fetchFalso.mockResolvedValueOnce(respuestaJson({ ok: true }));
    fetchFalso.mockResolvedValueOnce(respuestaJson({ id: 1 }, 201));

    await cliente.get('/padron/duenios');
    await cliente.post('/cobros/pagos', { monto: 1000 });

    expect(cabeceras(0).get('Authorization')).toBe('Bearer token-prueba');
    expect(cabeceras(1).get('Authorization')).toBe('Bearer token-prueba');
  });

  it('no envía Authorization cuando no hay token', async () => {
    const { cliente, fetchFalso, cabeceras } = crearClientePrueba({
      getToken: () => null,
    });

    fetchFalso.mockResolvedValueOnce(respuestaJson([]));

    await cliente.get('/guarderia/reservas');

    expect(cabeceras().get('Authorization')).toBeNull();
  });

  it('ante un 401 cierra la sesión y no reintenta', async () => {
    const onNoAutorizado = vi.fn();
    const { cliente, fetchFalso } = crearClientePrueba({ onNoAutorizado });

    fetchFalso.mockResolvedValueOnce(respuestaJson({ detail: 'No autorizado' }, 401));

    const error = await cliente.get('/panel').catch((fallo: unknown) => fallo);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ tipo: 'http', estado: 401 });
    expect(onNoAutorizado).toHaveBeenCalledTimes(1);
    expect(fetchFalso).toHaveBeenCalledTimes(1);
  });

  it('en el login un 401 muestra el error de credenciales y no cierra la sesión', async () => {
    const onNoAutorizado = vi.fn();
    const { cliente, fetchFalso } = crearClientePrueba({ onNoAutorizado });

    fetchFalso.mockResolvedValueOnce(respuestaJson({ detail: 'Credenciales inválidas' }, 401));

    await expect(
      cliente.post(
        '/auth/login',
        { username: 'ana', password: 'incorrecta' },
        { sinNotificarNoAutorizado: true },
      ),
    ).rejects.toThrow('Credenciales inválidas');

    expect(onNoAutorizado).not.toHaveBeenCalled();
  });

  it('muestra el mensaje de permisos que devuelve el servidor en un 403', async () => {
    const { cliente, fetchFalso } = crearClientePrueba();

    fetchFalso.mockResolvedValueOnce(
      respuestaJson({ detail: 'Bajar el precio requiere rol DUENIO.' }, 403),
    );

    await expect(cliente.post('/cobros/servicios/1/ajuste', { total: 900 })).rejects.toThrow(
      'Bajar el precio requiere rol DUENIO.',
    );
  });

  it('usa un mensaje propio cuando el 403 no trae detalle', async () => {
    const { cliente, fetchFalso } = crearClientePrueba();

    fetchFalso.mockResolvedValueOnce(new Response(null, { status: 403 }));

    await expect(cliente.get('/panel')).rejects.toThrow(
      'No tenés permiso para realizar esta acción.',
    );
  });

  it('reintenta un POST idempotente con la misma Idempotency-Key', async () => {
    const generarIdempotencyKey = vi.fn(() => 'clave-unica');
    const { cliente, fetchFalso, cabeceras } = crearClientePrueba({
      generarIdempotencyKey,
    });

    fetchFalso.mockRejectedValueOnce(new TypeError('Failed to fetch'));
    fetchFalso.mockResolvedValueOnce(respuestaJson({ id: 7 }, 201));

    const resultado = await cliente.post(
      '/cobros/pagos',
      { monto: 1000 },
      { idempotente: true },
    );

    expect(resultado).toEqual({ id: 7 });
    expect(fetchFalso).toHaveBeenCalledTimes(2);
    expect(generarIdempotencyKey).toHaveBeenCalledTimes(1);
    expect(cabeceras(0).get('Idempotency-Key')).toBe('clave-unica');
    expect(cabeceras(1).get('Idempotency-Key')).toBe('clave-unica');
  });

  it('no reintenta ni agrega Idempotency-Key en un POST común', async () => {
    const { cliente, fetchFalso, cabeceras } = crearClientePrueba();

    fetchFalso.mockRejectedValueOnce(new TypeError('Failed to fetch'));

    await expect(cliente.post('/padron/duenios', { dni: '12345678' })).rejects.toMatchObject({
      tipo: 'red',
    });

    expect(fetchFalso).toHaveBeenCalledTimes(1);
    expect(cabeceras().get('Idempotency-Key')).toBeNull();
  });

  it('respeta la Idempotency-Key provista por quien llama', async () => {
    const generarIdempotencyKey = vi.fn(() => 'no-deberia-usarse');
    const { cliente, fetchFalso, cabeceras } = crearClientePrueba({
      generarIdempotencyKey,
    });

    fetchFalso.mockResolvedValueOnce(respuestaJson({ id: 9 }, 201));

    await cliente.post(
      '/guarderia/reservas',
      { fecha: '2026-11-01' },
      { idempotencyKey: 'clave-ui', reintentos: 0 },
    );

    expect(cabeceras().get('Idempotency-Key')).toBe('clave-ui');
    expect(generarIdempotencyKey).not.toHaveBeenCalled();
  });

  it('no reintenta un GET que falla por red', async () => {
    const { cliente, fetchFalso } = crearClientePrueba();

    fetchFalso.mockRejectedValueOnce(new TypeError('Failed to fetch'));

    await expect(cliente.get('/padron/duenios')).rejects.toMatchObject({
      tipo: 'red',
      reintentable: true,
    });

    expect(fetchFalso).toHaveBeenCalledTimes(1);
  });

  it('devuelve undefined en un 204', async () => {
    const { cliente, fetchFalso } = crearClientePrueba();

    fetchFalso.mockResolvedValueOnce(new Response(null, { status: 204 }));

    await expect(cliente.delete('/guarderia/reservas/1')).resolves.toBeUndefined();
  });

  it('expone el detalle estructurado de un error de negocio', async () => {
    const { cliente, fetchFalso } = crearClientePrueba();

    fetchFalso.mockResolvedValueOnce(
      respuestaJson(
        {
          detail: {
            codigo: 'DNI_DUPLICADO',
            persona: { id: 4, nombre: 'Ana', apellido: 'Paz' },
          },
        },
        409,
      ),
    );

    const error = await cliente
      .post('/personas', { dni: '12345678' })
      .catch((fallo: unknown) => fallo);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      tipo: 'http',
      estado: 409,
      detalle: { codigo: 'DNI_DUPLICADO' },
    });
  });

  it('avisa cuando el servidor devuelve JSON inválido', async () => {
    const { cliente, fetchFalso } = crearClientePrueba();

    fetchFalso.mockResolvedValueOnce(new Response('no es json', { status: 200 }));

    await expect(cliente.get('/padron/duenios')).rejects.toMatchObject({
      tipo: 'respuesta',
      estado: 200,
    });
  });
});
