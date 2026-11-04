# Módulo cobros

- Responsable: Emiliano
- Expone por service.py: crear_cargo, registrar_pago, saldo_pendiente, ajustar_precio, cerrar_cargo_por_cancelacion (cierre auditable del saldo sin reversar pagos), registrar_gasto_externo
- Contrato con guardería (T-66): `CargoDetalleOut.reserva_estado` se completa llamando a
  `guarderia.service.estado_reserva(db, reserva_id)` solo cuando el cargo tiene
  `referencia_tipo == "RESERVA"`. Cobros no importa modelos ni repositorios de guardería y un
  estado ausente (reserva inexistente) no rompe la cuenta.
