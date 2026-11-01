# Módulo clínica

- Responsable: Aldana
- Historia clínica: `atencion` y `vacuna_aplicada`; no almacenan datos de pagos.
- Los servicios públicos `ultima_atencion`, `atenciones_de_paciente` y
  `registrar_atencion` permiten el consumo por otros módulos.
- Los datos de paciente y empleado se consultan únicamente mediante
  `padron.service`.
- Los endpoints de historia clínica usan el recurso `historia_clinica`: Dueño y
  Veterinario escriben; Personal solo lee.
- La agenda veterinaria se publica en T-41.
