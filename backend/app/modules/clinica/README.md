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
