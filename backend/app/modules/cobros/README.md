# Módulo cobros

- Responsable: Emiliano
- Spec asociada: docs/specs/cobros.md
- Expone por service.py: crear_cargo (previsto, se confirma en la spec), registrar_pago (previsto, se confirma en la spec), saldo_pendiente (previsto, se confirma en la spec), ajustar_precio (previsto, se confirma en la spec), cerrar_cargo_por_cancelacion (cierre auditable del saldo sin reversar pagos), registrar_gasto_externo (previsto, se confirma en la spec)
- Contrato con guardería (T-66): `CargoDetalleOut.reserva_estado` se completa llamando a
  `guarderia.service.estado_reserva(db, reserva_id)` solo cuando el cargo tiene
  `referencia_tipo == "RESERVA"`. Cobros no importa modelos ni repositorios de guardería y un
  estado ausente (reserva inexistente) no rompe la cuenta.
