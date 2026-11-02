# Módulo clínica

- Responsable: Aldana
- Historia clínica: `atencion` y `vacuna_aplicada`; no almacenan datos de pagos.
- Los servicios públicos `ultima_atencion`, `atenciones_de_paciente` y
  `registrar_atencion` permiten el consumo por otros módulos.
- Los datos de paciente y empleado se consultan únicamente mediante
  `padron.service`.
- Los endpoints de historia clínica usan el recurso `historia_clinica`: Dueño y
  Veterinario escriben; Personal solo lee.
- La agenda veterinaria y los turnos de personal usan el recurso `turnos`.
  Dueño, Personal y Veterinario pueden escribir turnos médicos; solo Dueño
  configura horarios, definiciones de turnos y asignaciones de personal.
- T-41 expone `/api/clinica/horarios`, `/api/clinica/turnos-personal`,
  `/api/turnos` y `/api/clinica/agenda`. Los horarios de atención y las
  definiciones de turnos comienzan vacíos: los horarios exactos los configura
  el Dueño. No se cargan feriados.
- Las reglas de agenda y sus validaciones viven en `service.py`; las
  transiciones de estado en `estados.py`, la validación de horarios en
  `horarios.py` y el cálculo puro de traspasos en `traspaso.py`.
- La clínica consulta pacientes y empleados únicamente mediante
  `padron.service`; la agenda común solo permite veterinarios internos.
- `/api/clinica/veterinarios` devuelve los empleados internos activos con perfil
  veterinario y usuario activo de rol `VETERINARIO`; requiere acceso de lectura
  a turnos.

## Pendientes

- **Pantalla de Administración para los horarios de atención.** Hoy solo se
  definen con `PUT /api/clinica/horarios` (Dueño); sin horarios cargados, el
  alta de turnos responde "Aún no se definieron horarios de atención". Ticket
  propio de `clinica` (frontend + spec).

## Cobro del turno

- `POST /api/turnos` acepta `monto_centavos` (opcional, entero positivo). Si viene, clínica llama a `cobros.service.crear_cargo` (referencia `TURNO` y el id del turno) a nombre del **titular principal vigente** de la mascota, en la misma transacción del turno: si el turno falla no queda cargo. Mismo acuerdo que el de estudios (T-40). La tabla `turno` guarda solo el `cargo_id`, no el dinero.
- La deuda se calcula en Cobros (total menos pagos); el turno no registra pagos. Una mascota sin titular principal rechaza el monto (422 `SIN_TITULAR`).
- Pendiente: cancelar o marcar ausente un turno **no** anula su cargo; hace falta un ajuste desde Cobros.
