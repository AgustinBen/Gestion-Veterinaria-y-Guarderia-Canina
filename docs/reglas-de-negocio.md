# Glosario y catálogo de reglas de negocio (v0.4)

Fecha: 2026-10-25. Fuentes: enunciado, documentos de alcance y plan, apuntes de entrevistas (Grupo 1), Excel histórico, respuestas de Agustín, decisiones del equipo del 2026-10-21 y revisión cruzada de Aldana y Emiliano sobre las reglas supuestas (registro en la sección 6).

**Aclaración de fuentes:** las respuestas "del cliente" sobre gatos, franjas, DNI, deudas y cupo de emergencia las informó Agustín. **No constan en los apuntes escritos** (los apuntes no mencionan gatos). Conviene tener constancia escrita (fecha y medio).

**Estado de cada regla:**
- `CONFIRMADA`: la dijo el cliente.
- `DECIDIDA`: decisión aprobada por el equipo (la fecha y el motivo están en la sección 6). **No es una confirmación del cliente**: si el cliente la contradice, se revisa.
- `PENDIENTE`: hay una pregunta abierta para el cliente (ver sección 5).

**Principio rector (nota del cliente):** el sistema debe ser simple para personal no técnico y su objetivo es que el negocio no pierda dinero por mal registro. Si un dato se puede calcular, el usuario no lo carga a mano (por ejemplo, la deuda o la edad).

## 1. Glosario
| Término | Significado |
|---|---|
| Dueño (tutor) | Persona responsable de una o más mascotas. Se identifica con DNI. |
| Mascota (paciente) | Animal atendido (perro o gato). Tiene historia clínica propia y puede tener más de un dueño. |
| Franja | Mitad del día para la guardería: **Día** o **Noche**. La guardería abre 24 h. |
| Plaza | Un lugar en la guardería. **Cada animal ocupa exactamente 1 plaza por franja**, sin importar especie ni tamaño. |
| Cupo | Cantidad máxima de plazas por fecha y franja. Configurable (8 a 10). Lo ajusta el Dueño. |
| Plaza de emergencia | Plaza reservada por día dentro del cupo, no disponible para reserva pública. |
| Servicio | Lo que se cobra: una atención clínica o una estadía de guardería. |
| Cotización | Precio calculado para un servicio. Se puede ajustar (ver RN-22). |
| Seña | Pago anticipado, de monto variable según el servicio. |
| Pago | Dinero recibido con monto, medio, fecha y empleado que lo registró. |
| Saldo | Total del servicio menos la suma de pagos. |
| Deuda | Saldo mayor a cero. Se calcula automáticamente. "Fiado" es un servicio con pagos en cero. |
| Veterinario clínico | Trabaja en el local en la sección veterinaria. |
| Especialista externo | Veterinario o profesional llamado cuando se necesita (cirugía, anestesia, estética). No tiene usuario en el sistema. |
| Turno de personal | Mañana, Tarde o Noche, con 30 minutos de traspaso de información entre turnos. |

## 2. Reglas de negocio

### Dueños y mascotas
- **RN-01** El cliente nuevo se registra con DNI, nombre, apellido y teléfono. La dirección es opcional. `CONFIRMADA`
- **RN-02** El DNI es único cuando existe y un DNI repetido **bloquea** el alta. Los clientes migrados del Excel pueden no tenerlo y se completa en su próxima visita. `DECIDIDA`
- **RN-03** Una mascota puede tener más de un dueño. Uno figura como titular principal y responsable de pago. `CONFIRMADA` (varios dueños); `DECIDIDA` (principal)
- **RN-04** Se puede cambiar el dueño de una mascota y su historia clínica se conserva. `CONFIRMADA`
- **RN-05** La especie es obligatoria (perro o gato). `CONFIRMADA`
- **RN-06** Un teléfono repetido o un nombre parecido avisan y exigen una confirmación explícita, que queda registrada. El sistema nunca fusiona automáticamente. `DECIDIDA`
- **RN-07** Características y comportamiento de la mascota y del dueño se anotan en un campo propio, separado de lo clínico y de los pagos. `CONFIRMADA`
- **RN-08** Nombre y apellido son obligatorios. Los empleados migrados sin apellido (por ejemplo "Dra. Laura") se completan a mano antes de cargarlos. `DECIDIDA`
- **RN-09** Se guarda la fecha de nacimiento aproximada de la mascota. La edad se calcula y no se guarda. `DECIDIDA`

### Guardería
- **RN-10** Las franjas son Día y Noche. El "medio día" del Excel se migra como Día. `CONFIRMADA`
- **RN-11** El cupo se controla por fecha y franja. **Cada animal ocupa 1 plaza**: perros y gatos comparten el mismo cupo y el tamaño no interviene. `CONFIRMADA` (gatos, informado por Agustín); `DECIDIDA` (tamaño no interviene, decisión de alcance del 2026-10-21)
- **RN-11b** El cupo máximo es configurable y el Dueño puede bajarlo cuando haya muchos perros grandes. **Riesgo conocido:** los apuntes dicen "entre 10 y 8 perros (depende del tamaño)"; con 1 plaza por animal el sistema puede aceptar más perros grandes de los que el patio soporta. La regla de ocupación debe vivir en una sola función para poder cambiarla rápido. `DECIDIDA`
- **RN-12** Una estadía que cubre día y noche ocupa una plaza en cada franja. Un animal que ingresa de día y permanece durante la noche cuenta en ambas. `DECIDIDA` (aprobada por Aldana y Emiliano); `PENDIENTE` (pregunta 3 al cliente)
- **RN-13** Plaza de emergencia: el cupo público es el cupo máximo menos las plazas de emergencia (por defecto 1, parametrizable). Con cupo 10, se pueden reservar 9. `CONFIRMADA`
- **RN-14** Habilitar una plaza de emergencia para reserva pública requiere una acción explícita de un usuario con rol **Dueño**, registrada con quién, cuándo, para qué fecha y franja, y motivo. `CONFIRMADA` (requisito de habilitación explícita); `DECIDIDA` (rol: solo el Dueño, **provisional**: el requisito original decía "firmada por el veterinario a cargo"; ver pregunta 11 al cliente)
- **RN-15** Una reserva que supera el cupo disponible se rechaza. La única forma de ampliar es RN-14 o que el Dueño suba el cupo máximo. `DECIDIDA` (aprobada por Aldana y Emiliano)
- **RN-16** Se puede reservar hasta 4 meses a futuro. `CONFIRMADA`
- **RN-17** Reservar en guardería exige una seña obligatoria, de monto libre. `CONFIRMADA`
- **RN-18** Descuento automático del 20% sobre la tarifa diaria total cuando un mismo tutor reserva a la vez para dos o más mascotas. `CONFIRMADA` (detalles en PENDIENTE)
- **RN-19** La tarifa depende de la franja, la cantidad de días y los cuidados extras (sí o no). `CONFIRMADA`

### Cobros y deudas
- **RN-20** Cada servicio tiene un total y uno o más pagos (seña, parciales, saldo). Cada pago registra monto, medio (efectivo, débito, transferencia, Mercado Pago), fecha y empleado. `CONFIRMADA`
- **RN-21** La deuda se calcula como total menos pagos. No se carga a mano. `DECIDIDA` (aprobada por Aldana y Emiliano)
- **RN-22** **Ajuste de precio:** el precio calculado se puede cambiar a último momento, mientras el servicio no esté pagado por completo. El nuevo total no puede ser menor a lo ya pagado. **Subir el precio** lo puede hacer cualquier usuario con permiso de cobrar (Dueño o Personal). **Bajar el precio** solo lo puede hacer el Dueño. Cada ajuste guarda precio anterior, precio nuevo, motivo y usuario. `CONFIRMADA` (poder cambiarlo); `DECIDIDA` (límites, auditoría y quién puede bajarlo, 2026-10-25); `PENDIENTE` (pregunta 12 al cliente)
- **RN-23** La deuda no impide retirar la mascota ni contratar nuevos servicios. El sistema solo muestra una alerta visible (puede pedir una confirmación en pantalla, pero no bloquea). Restringir nuevos servicios es una decisión humana de empleados y dueño. `CONFIRMADA`
- **RN-24** La seña no es un porcentaje fijo y varía según el servicio. `CONFIRMADA`

### Clínica y personal
- **RN-30** Cada mascota tiene su propia historia clínica (consultas, vacunas, cirugías, tratamientos), separada de los pagos. `CONFIRMADA`
- **RN-31** Una cirugía (por ejemplo castración) requiere un veterinario externo, que se registra con su costo. `CONFIRMADA`
- **RN-32** La agenda veterinaria funciona en un horario acotado. Los turnos de personal son Mañana, Tarde y Noche, con 30 minutos de traspaso. `CONFIRMADA`
- **RN-33** Cada servicio registra qué empleado o veterinario lo realizó. `CONFIRMADA`

### Roles y migración
- **RN-40** Hay tres roles: **Dueño**, **Personal** (recepción) y **Veterinario**. El acceso se define en una matriz rol × recurso (ver sección 3). El rol define los permisos; que alguien sea veterinario es un dato del empleado. Las deudas están separadas de las finanzas. `CONFIRMADA` (separación de finanzas y deudas); `DECIDIDA` (matriz, aprobada por Aldana y Emiliano; con la excepción de la historia clínica para Personal, que sigue `PENDIENTE`)
- **RN-50** Todos los datos del Excel se migran, incluidas las deudas, como saldo pendiente con origen "migración". Se conserva el texto original de cada registro. `CONFIRMADA` (migrar todo); `DECIDIDA` (conservar el texto, aprobada por Aldana y Emiliano)

## 3. Matriz de acceso (`DECIDIDA` por el equipo)
| Recurso | Dueño | Personal | Veterinario |
|---|---|---|---|
| Usuarios y configuración | Sí | No | No |
| Finanzas, métricas, gastos a externos y detalle de servicios por cliente | Sí | No | No |
| Deudas y cobros | Sí | Sí | No |
| Listado global de deudores (pantalla Deudores) | Sí | No | No |
| Subir el precio de un servicio (RN-22) | Sí | Sí | No |
| Bajar el precio de un servicio (RN-22) | Sí | No | No |
| Padrón (dueños y mascotas) | Sí | Sí | Solo lectura |
| Reservas de guardería y cupo | Sí | Sí | Solo lectura |
| Habilitar plaza de emergencia (RN-14, provisional) | Sí | No | No |
| Turnos veterinarios | Sí | Sí | Sí |
| Historia clínica | Sí | Solo lectura (a validar con el cliente) | Sí, con escritura |

El **listado global de deudores** se considera información financiera/detalle por cliente: solo lo ve el Dueño. Personal conserva el acceso a deudas y cobros y ve la deuda dentro de la cuenta de cada cliente.

## 4. Fuera del MVP 1
Karma de confiabilidad, notificaciones, portal para dueños, política automatizada de cancelaciones, reportes avanzados y cupo según el tamaño del animal.

## 5. Pendientes de validar con el cliente
1. **Plaza de emergencia:** ¿una por día calendario o una por franja (día y noche)?
2. **Descuento del 20%:** ¿qué cuenta como "simultánea"? ¿Aplica desde la primera mascota?
3. **Día y noche:** ¿son cupos independientes? ¿Una estadía de 24 h ocupa ambos?
4. **Varios dueños:** ¿todos se registran con DNI? ¿Los contactos alternativos también?
5. **Placas:** ¿se guarda la imagen o solo el registro de que se hizo y su costo?
6. **Personal y clínica:** ¿recepción puede ver el historial clínico (solo lectura)?
7. **Cupo según el tamaño (riesgo de RN-11b):** si ya hay 6 perros grandes, ¿cuántos chicos más entran? ¿Y si son todos chicos, el tope también es 10?
8. **Excel:** cantidad real de filas, fecha de la última edición (fecha de corte para calcular edades) y si las deudas siguen vigentes.
9. **Constancia escrita** de que los gatos comparten el cupo.
10. **Despliegue:** sistema operativo de la PC del local, si está prendida las 24 h y si el Dueño acepta ver el panel solo desde el local.
11. **Quién habilita la plaza de emergencia:** hoy solo el Dueño (decisión provisional del equipo). El requisito original hablaba de "habilitación firmada por el veterinario a cargo". ¿Alcanza con el Dueño o tiene que intervenir un veterinario?
12. **Descuentos y bajas de precio:** hoy solo el Dueño puede bajar un precio ya calculado (por ejemplo, la bonificación del 50% a un cliente frecuente que aparece en el Excel). ¿Es correcto o recepción también tiene que poder hacerlo?

## 6. Registro de decisiones
| Fecha | Decisión | Motivo |
|---|---|---|
| 2026-10-19 | Cada animal ocupa 1 plaza. Se eliminan los factores por tamaño. | Simplicidad; los factores propuestos (1 / 0,75 / 0,5) no coincidían con el máximo de 10 perros del cliente. |
| 2026-10-19 | Gatos y perros comparten cupo. | Respuesta del cliente informada por Agustín. |
| 2026-10-19 | Tres roles con matriz de acceso. | El alcance y los apuntes los piden; la matriz hace barato cambiar permisos. |
| 2026-10-19 | El ajuste de precio se permite hasta el pago total, con auditoría. | La seña obligatoria impediría ajustar si se bloqueara al primer pago. |
| 2026-10-20 | Despliegue local en una PC del negocio, acceso solo por LAN, sin hosting. | Confirmado por Agustín. Afecta a backups, instalación y mala señal (T-53, T-54). |
| 2026-10-21 | D1: se mantiene la entidad `cliente`. D10: teléfonos N por persona. D11: una tabla de empleado con `tipo`. D12: `titularidad` con vigencia. D9: domicilio en una sola tabla con columnas separadas. | Decisión del equipo; se siguió el ticket T-05. Para D9 se evaluó el DER de 5 tablas y se descartó por ahora: `Domicilio` solo apunta a `Calle` (no a la localidad ni al código postal), `piso` y `numero` son enteros, los catálogos arrancan vacíos y sumaba unas 6 a 8 h en el camino crítico. Evolución posible: catálogo solo de localidad. |
| 2026-10-21 | D2: tablas `especie` y `raza`, con alta rápida. D3: tamaño solo descriptivo. D13: apellido obligatorio. | Normalizar es un objetivo del proyecto; no cuesta más que lo ya planeado en T-11. |
| 2026-10-21 | D4 y D5: DNI único con bloqueo; teléfono repetido y nombre parecido avisan con confirmación explícita. | La recepción no debe verse empujada a inventar teléfonos. |
| 2026-10-21 | D6: el rol define permisos; `es_veterinario` es un dato del empleado. | Los cirujanos externos no tienen usuario. |
| 2026-10-21 | D7: se guarda la fecha de nacimiento aproximada y la edad se calcula. | Lo calculable no se guarda. |
| 2026-10-21 | D8: ante pesos en conflicto, gana la fila posterior y queda en el reporte. | El Excel no tiene fechas por fila. |
| 2026-10-21 | D14: el tamaño no interviene en el cupo; 10 plazas admiten 10 animales. | Decisión de alcance de Agustín: evita un cálculo extra. Riesgo registrado en RN-11b. |
| 2026-10-21 | Por ahora el trabajo se limita a los tickets T-01 a T-10. | Fecha de entrega del MVP: 2026-11-05. |
| 2026-10-25 | Aldana y Emiliano aprueban RN-12, RN-15, RN-21, RN-22, RN-40 (matriz) y RN-50, que pasan de `SUPUESTO` o `PROPUESTA` a `DECIDIDA`. | Revisión cruzada del PR de specs de T-05. Siguen siendo decisiones del equipo, no confirmaciones del cliente. |
| 2026-10-25 | RN-22: subir el precio lo puede hacer quien cobra (Dueño o Personal); bajarlo solo el Dueño. | Emiliano propuso que el precio solo pudiera subir para evitar pérdidas; Aldana lo leyó como la regla escrita (sube o baja). Se eligió una opción intermedia: se mantienen los descuentos (hay una bonificación del 50% en el Excel) pero con control del Dueño. |
| 2026-10-25 | RN-14: la plaza de emergencia solo la habilita el Dueño (antes, Veterinario o Dueño). **Provisional.** | Decisión de Agustín, "por ahora". Se aparta del requisito original ("firmada por el veterinario a cargo"); queda como pregunta 11 al cliente. |
| 2026-10-29 | El listado global de deudores es solo del Dueño; Personal conserva deudas y cobros en la cuenta del cliente. | Evitar que Personal acceda al listado global desde el botón "Ver deudores" de Cobros. Se considera información financiera/detalle por cliente. |

## 7. Documentos a corregir (tickets y agentes con texto viejo)
- `AGENTS.md` (PR #15 de Aldana): plaza de emergencia solo para Dueño (rol, matriz y regla de guardería); precio: subir cualquier rol con permiso de cobro, bajar solo Dueño; encabezado que no diga que todo `SUPUESTO` es `DECIDIDA` y remita a este documento; cerrar el bloque de código de la sección 4; reponer la sección de seguridad y datos (secretos, `.env`, `.db`, Excel real fuera del repo, contraseñas con hash).
- `opencode.json` (PR #15): la clave correcta es `permission` (objeto), no `permissions` (lista); quitar el modelo fijo.
- `README.md` (PR #15): ya no hay seis agentes especializados.
- `docs/specs/identidad.md`: matriz con "Habilitar plaza de emergencia" solo para Dueño, y la línea de RN-14 que dice "VETERINARIO o DUENIO". Agregar las filas de subir y bajar precio.
- `docs/specs/cobros.md` (T-06): incluir la regla de RN-22 (bajar precio solo `DUENIO`) en el ajuste de precio y en los endpoints.
- `qa-tester.md` y `code-reviewer.md` ya no existen en el repo (PR #15); si se retoman, quitar "tamaños mixtos" y usar la matriz de tres roles.
- Tickets: T-07, T-18 y T-24 (cupo sin factor, regla en una sola función), T-09 (menú Panel solo para Dueño, tres roles), T-10 (tres roles y `GET /api/usuarios`), T-11 (`tamanio` sin factor, `cliente`, domicilio con `referencia`, `tipo_contacto`, `especie` y `raza`), T-12 (DNI bloquea, teléfono y nombre avisan, alta rápida de razas), T-16 (apellido faltante, fecha de corte, gana la fila posterior), T-20 y T-31 (bajar precio solo `DUENIO`), T-33 (habilitar plaza de emergencia solo `DUENIO`) y T-35 (la acción de habilitar plaza de emergencia solo visible para el Dueño).
