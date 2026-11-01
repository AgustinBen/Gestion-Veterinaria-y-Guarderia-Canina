# Módulo guardería

- Responsable: Aldana
- Servicio público: `disponibilidad`, `calendario`, `verificar_cupo`,
  `franjas_del_tramo`, `habilitar_plaza_emergencia` y `cancelar_reserva`.
- `ReservaOut.sena_centavos` expone el total neto de señas por el recurso
  `reservas_cupo`, sin exponer pagos ni saldos de Cobros.
- Cada paciente de una reserva conserva el indicador de cuidados extras y su
  detalle opcional en `reserva_paciente`.
- El rango máximo del calendario se configura en Settings con
  `GUARDERIA_CALENDARIO_MAX_DIAS` (por defecto, 366).
- El cupo máximo y las plazas de emergencia se leen desde la configuración del
  módulo en cada consulta.
- La habilitación de emergencia es explícita, idempotente y exclusiva del Dueño.
- La cancelación manual de reservas pendientes o confirmadas libera sus
  ocupaciones, conserva los pagos y cierra el saldo mediante Cobros con un
  ajuste auditable. Dueño y Personal pueden cancelarlas.

## Coordinación con T-25 y T-34

- T-25 debe consultar la clave de idempotencia antes de verificar el cupo y
  realizar la verificación y la escritura de reserva en una misma operación
  transaccional que impida sobreventas concurrentes.
- T-34 debe conservar esta política al integrar cambios de cancelación:
  liberar las ocupaciones de reservas pendientes o confirmadas y preservar el
  historial de cobros, sin reversar pagos.
