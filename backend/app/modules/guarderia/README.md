# Módulo guardería

- Responsable: Aldana
- Servicio público: `disponibilidad`, `calendario`, `verificar_cupo` y
  `franjas_del_tramo`.
- `ReservaOut.sena_centavos` expone el total neto de señas por el recurso
  `reservas_cupo`, sin exponer pagos ni saldos de Cobros.
- Cada paciente de una reserva conserva el indicador de cuidados extras y su
  detalle opcional en `reserva_paciente`.
- El rango máximo del calendario se configura en Settings con
  `GUARDERIA_CALENDARIO_MAX_DIAS` (por defecto, 366).
- El cupo máximo y las plazas de emergencia se leen desde la configuración del
  módulo en cada consulta.

## Coordinación con T-25 y T-34

- T-25 debe consultar la clave de idempotencia antes de verificar el cupo y
  realizar la verificación y la escritura de reserva en una misma operación
  transaccional que impida sobreventas concurrentes.
- T-34 debe definir y probar cómo la cancelación manual libera las filas de
  `ocupacion`, y qué estados conservan o liberan plazas. Hasta entonces, el
  motor cuenta todas las filas de ocupación y no infiere una regla a partir del
  estado de la reserva.
