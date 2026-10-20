# Glosario y catálogo de reglas de negocio (v0.1)

Fecha: 2026-10-19. Fuentes: enunciado, documentos de alcance y plan, apuntes de entrevistas (Grupo 1), Excel histórico y respuestas del líder del equipo (que habló con el cliente).

**Estado de cada regla:** `CONFIRMADA` (la dijo el cliente), `SUPUESTO` (decisión nuestra, hay que validarla), `PENDIENTE` (ver sección 4).

**Principio rector (nota del cliente):** el sistema debe ser simple para personal no técnico y su objetivo es que el negocio no pierda dinero por mal registro. Si un dato se puede calcular, el usuario no lo carga a mano (por ejemplo, la deuda).

## 1. Glosario
| Término | Significado |
|---|---|
| Dueño (tutor) | Persona responsable de una o más mascotas. Se identifica con DNI. |
| Mascota (paciente) | Animal atendido. Tiene especie (perro o gato), historia clínica propia y puede tener más de un dueño. |
| Franja | Mitad del día para la guardería: **Día** o **Noche**. La guardería abre 24 h. |
| Plaza | Un lugar en la guardería. Cada animal ocupa una plaza por franja. |
| Cupo | Cantidad máxima de plazas por fecha y franja. Configurable, entre 8 y 10. |
| Plaza de emergencia | Plaza reservada por día dentro del cupo, no disponible para reserva pública. |
| Servicio | Lo que se cobra: una atención clínica o una estadía de guardería. |
| Cotización | Precio calculado para un servicio. Se puede modificar hasta cobrar. |
| Seña | Pago anticipado, de monto variable según el servicio. |
| Pago | Dinero recibido con monto, medio, fecha y empleado que lo registró. |
| Saldo | Total del servicio menos la suma de pagos. |
| Deuda | Saldo mayor a cero. Se calcula automáticamente. "Fiado" es un servicio con pagos en cero. |
| Veterinario clínico | Trabaja en el local en la sección veterinaria. |
| Especialista externo | Veterinario o profesional llamado cuando se necesita (cirugía, anestesia, estética). |
| Turno de personal | Mañana, Tarde o Noche, con 30 minutos de traspaso de información entre turnos. |

## 2. Reglas de negocio

### Dueños y mascotas
- **RN-01** El cliente nuevo se registra con DNI, nombre, apellido y teléfono. La dirección es opcional. `CONFIRMADA`
- **RN-02** El DNI es único cuando existe. Los clientes migrados del Excel pueden no tenerlo y se completa en su próxima visita. `SUPUESTO`
- **RN-03** Una mascota puede tener más de un dueño. Uno figura como titular y responsable de pago. `CONFIRMADA` (varios dueños); `SUPUESTO` (titular)
- **RN-04** Se puede cambiar el dueño de una mascota y su historia clínica se conserva. `CONFIRMADA`
- **RN-05** La especie es obligatoria (perro o gato). `CONFIRMADA`
- **RN-06** Al crear una mascota o un dueño, el sistema avisa si ya existe una coincidencia (mismo dueño y nombre de mascota, o mismo teléfono) y nunca fusiona automáticamente. `SUPUESTO`
- **RN-07** Características y comportamiento de la mascota y del dueño se anotan en un campo propio, separado de lo clínico y de los pagos. `CONFIRMADA`

### Guardería
- **RN-10** Las franjas son Día y Noche. El "medio día" del Excel se migra como Día. `CONFIRMADA`
- **RN-11** El cupo se controla por fecha y franja. Cuenta animales, y perros y gatos ocupan el mismo cupo. `CONFIRMADA`
- **RN-12** Una estadía que cubre día y noche ocupa una plaza en cada franja. `SUPUESTO`
- **RN-13** Plaza de emergencia: el cupo público es el cupo máximo menos las plazas de emergencia (por defecto 1, parametrizable). `CONFIRMADA`
- **RN-14** Habilitar una plaza de emergencia para reserva pública requiere una acción explícita del veterinario a cargo, registrada con quién, cuándo, para qué fecha y franja, y motivo. `CONFIRMADA`
- **RN-15** Una reserva que supera el cupo disponible se rechaza. La única forma de ampliar es RN-14. `SUPUESTO`
- **RN-16** Se puede reservar hasta 4 meses a futuro. `CONFIRMADA`
- **RN-17** Reservar en guardería exige una seña obligatoria, de monto libre. `CONFIRMADA`
- **RN-18** Descuento automático del 20% sobre la tarifa diaria total cuando un mismo tutor reserva a la vez para dos o más mascotas. `CONFIRMADA` (detalles en PENDIENTE)
- **RN-19** La tarifa depende de la franja, la cantidad de días y los cuidados extras (sí o no). `CONFIRMADA`

### Cobros y deudas
- **RN-20** Cada servicio tiene un total y uno o más pagos (seña, parciales, saldo). Cada pago registra monto, medio (efectivo, débito, transferencia, Mercado Pago), fecha y empleado. `CONFIRMADA`
- **RN-21** La deuda se calcula como total menos pagos. No se carga a mano. `SUPUESTO`
- **RN-22** El precio puede cambiarse hasta antes de cobrar. Se guardan el precio calculado, el precio final y el motivo. `CONFIRMADA` (cambiar); `SUPUESTO` (guardar motivo)
- **RN-23** La deuda no impide retirar la mascota ni contratar nuevos servicios. El sistema solo muestra una alerta visible. Restringir nuevos servicios es una decisión humana de empleados y dueño. `CONFIRMADA`
- **RN-24** La seña no es un porcentaje fijo y varía según el servicio. `CONFIRMADA`

### Clínica y personal
- **RN-30** Cada mascota tiene su propia historia clínica (consultas, vacunas, cirugías, tratamientos), separada de los pagos. `CONFIRMADA`
- **RN-31** Una cirugía (por ejemplo castración) requiere un veterinario externo, que se registra con su costo. `CONFIRMADA`
- **RN-32** La agenda veterinaria funciona en un horario acotado. Los turnos de personal son Mañana, Tarde y Noche, con 30 minutos de traspaso. `CONFIRMADA`
- **RN-33** Cada servicio registra qué empleado o veterinario lo realizó. `CONFIRMADA`

### Roles y migración
- **RN-40** Dueño del negocio: finanzas y métricas. Empleado/Recepción: deudas, turnos y guardería. Veterinario clínico: historial médico. Las deudas están separadas de las finanzas. `CONFIRMADA`
- **RN-50** Todos los datos del Excel se migran, incluidas las deudas, como saldo pendiente con origen "migración". Se conserva el texto original de cada registro. `CONFIRMADA` (migrar todo); `SUPUESTO` (conservar el texto)

## 3. Fuera del MVP 1
Karma de confiabilidad, notificaciones, portal para dueños, política automatizada de cancelaciones y reportes avanzados.

## 4. Pendientes de validar con el cliente
1. **Plaza de emergencia:** ¿es una por día calendario o una por franja (día y noche)?
2. **Descuento del 20%:** ¿qué cuenta como "simultánea" (misma operación de reserva, o fechas que se superponen)? ¿Aplica desde la primera mascota?
3. **Día y noche:** ¿son cupos independientes? ¿Una estadía de 24 h ocupa ambos?
4. **Tamaño del perro:** los apuntes dicen que el cupo es de 8 a 10 "según el tamaño". ¿Basta un número configurable que cambie el dueño, o debe calcularse por tamaño?
5. **Varios dueños:** ¿se registran todos con DNI? ¿Quién figura como responsable de pago?
6. **Placas:** ¿se guarda la imagen o solo el registro de que se hizo y su costo?

## 5. Inconsistencias a corregir en documentos anteriores
- El documento de alcance habla de cotizar por "raza y comportamiento"; los apuntes dicen franja, días y cuidados extras (RN-19).
- Se habla de "perros" donde el cupo cuenta animales (RN-11).
- La plaza de emergencia (RN-13, RN-14) y el descuento multimascota (RN-18) son requisitos nuevos que no están en el plan de 230 horas. Hay que registrarlos como cambio de alcance.
