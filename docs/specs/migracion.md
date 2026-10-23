# Spec: migracion

**Responsable:** Agustín · **Módulo:** `backend/app/modules/migracion/` y `backend/scripts/migracion/` · **Tickets:** T-15, T-16, T-27, T-48 · **Reglas:** `docs/reglas-de-negocio.md`

## Estado
Borrador v0.2 (2026-10-21). Decisiones D7, D8 y D13 cerradas (registro en la sección 6 de `docs/reglas-de-negocio.md`). La hoja de clientes está definida. Las hojas de atenciones y guardería dependen de las specs de `clinica`, `cobros` y `guarderia` (T-06, T-07): su mapeo es de alto nivel y se completa cuando existan.

## Objetivo
Limpiar, normalizar y cargar la planilla histórica al modelo nuevo sin perder datos, sin duplicar y dejando a una persona todo lo dudoso. Se carga solo a través de los `service.py` de cada módulo.

## Reglas de negocio que implementa
- **RN-50:** se migra todo, incluidas las deudas (saldo pendiente con origen "migración"). El texto original de cada registro se conserva siempre.
- **RN-02:** los clientes migrados pueden no tener DNI. **RN-05:** la especie es obligatoria (hay gatos). **RN-10:** "medio día" se migra como Día. **RN-08:** el apellido es obligatorio; si falta, el registro va a revisión y se completa a mano.
- **RN-06:** nunca se fusiona por similitud de texto.
- El Excel original es de solo lectura, no va al repositorio (tiene datos personales) y se trabaja sobre una copia en `data/`.

## Fuente (muestra de 3 hojas)
| Hoja | Columnas | Filas |
|---|---|---|
| Clientes_y_Mascotas | ID_Registro, Nombre_Duenio, Telefono_Contacto, Nombre_Mascota, Especie_Raza, Edad_Aprox, Peso_Kg, Direccion_Localidad | 12 (9 personas, 11 mascotas, 1 duplicada) |
| Atenciones_Clinicas | Nro_Ficha, Fecha_Visita, Paciente_Mascota, Duenio_Referencia, Tipo_Servicio, Detalle_Clinico_y_Cobro, Veterinario_Tratante | 10 |
| Guarderia_y_Estadias | Nro_Reserva, Mascota, Tutor, Fecha_Ingreso, Fecha_Egreso, Modalidad, Tarifa_Total, Estado_Pago, Comportamiento_Cuidados | 10 |

## Mapeo a entidades
**Hoja 1 (T-16, vía `padron.service`)**
| Columna | Destino | Regla |
|---|---|---|
| ID_Registro | `migracion_origen` | no es clave (hay `REG-001`, `002`, `4`) |
| Nombre_Duenio | persona.nombre, apellido | quitar títulos (Dr., Dra.); el último término es el apellido; un solo término u otros casos dudosos, a revisión |
| Telefono_Contacto | telefono | normalizado; "Sin telefono" crea la persona sin teléfono |
| Nombre_Mascota | paciente.nombre | |
| Especie_Raza | paciente.especie, raza, tamaño | diccionario editable; razas nuevas se crean por `padron.service`; sin especie deducible, a revisión |
| Edad_Aprox | paciente.fecha_nacimiento_aprox | fecha de corte menos la edad |
| Peso_Kg | paciente.peso_kg | |
| Direccion_Localidad | domicilio | calle, número y piso si se reconocen; siempre `referencia` = texto original |

**Hojas 2 y 3 (T-27 y T-48, a completar con T-06 y T-07).** Mascota y dueño se asocian por (titular normalizado, nombre de mascota normalizado). `Detalle_Clinico_y_Cobro` se separa: lo clínico va a `clinica`, monto, medio de pago y deuda a `cobros`, y todo lo ambiguo a revisión. `Estado_Pago` (texto libre) genera pagos y saldo. `Modalidad` define la franja (RN-10). `Comportamiento_Cuidados` va a las notas del paciente (T-36). `Veterinario_Tratante` crea o busca un empleado INTERNO veterinario; como solo trae nombre de pila, va a revisión y el apellido se completa a mano antes de cargarlo.

## Reglas de normalización
| Dato | Regla |
|---|---|
| Teléfono | ver `padron.md`. Salida: 10 dígitos |
| Fecha | formatos reconocidos: `dd/mm/aaaa`, `aaaa-mm-dd`, `d de Mes aaaa` (mes en español), `dd/mm/aa`. Se asume día antes que mes. Salida ISO. Fecha inválida a revisión |
| Edad | "4 años", "4" (años), "2 años y medio", "6 meses", "3 años aprox" |
| Peso | quitar "kg", coma a punto. Fuera del rango configurado (`migracion.peso_max_kg`) a revisión |
| Especie y raza | `Perro - Labrador`, `canino`, `Gata Siamesa`, `Mestizo mediano`. Sin especie explícita ni en el diccionario, a revisión (nunca se asume) |
| Nombres | recortar espacios, capitalizar ("VALERIA GOMEZ" pasa a "Valeria Gomez"); comparar sin tildes ni mayúsculas |

**Ejemplos de teléfono (criterio de aceptación)**
| Entrada | Salida |
|---|---|
| `11 4455-8899` y `+5491144558899` | `1144558899` (misma persona) |
| `15-6677-2233` y `011 6677-2233` | `1166772233` |
| `011 4890-1122` y `1148901122` | `1148901122` |
| `+54 9 11 3322 1100` | `1133221100` |
| `0341-155443322` | `3415443322` |
| `Sin telefono (dejo mail)` | sin teléfono |

## Política de duplicados
- **Misma persona:** mismo teléfono normalizado y mismo nombre y apellido normalizados.
- Mismo teléfono con otro nombre: personas distintas (familia). Se lista en el reporte.
- Mismo nombre con otro teléfono: no se fusiona y va a revisión.
- **Misma mascota:** mismo titular y nombre normalizado **idéntico**. "Rocco" y "Rocco Jr." son animales distintos. No se usa similitud difusa.
- Datos en conflicto (peso de Firulais: 28,5 y 29): gana la fila posterior y ambas quedan en el reporte.

## A revisión manual
Todo lo dudoso se escribe en `revision.csv` y no se carga: `hoja, fila, id_origen, campo, valor_original, motivo, accion_sugerida`. Nada se descarta ni se corrige en silencio. Los montos y las deudas ambiguos los revisa una persona antes de cargarse. Los empleados sin apellido esperan a que se complete.

## Ejecución e idempotencia
- Modo `--dry-run` (no escribe) y modo carga.
- Tabla propia `migracion_origen` (hoja, id_fila_origen, hash_fila, entidad, entidad_id, corrida). Repetir la corrida no duplica; si el hash de una fila cambió, va a revisión y no pisa datos.
- Informe final: filas leídas, cargadas, fusionadas y enviadas a revisión.

## Criterios de aceptación
- Con el Excel de muestra: 9 personas, 11 mascotas, Firulais una sola vez, Rocco y Rocco Jr. separados.
- Los teléfonos de ejemplo dan el resultado esperado.
- Dos corridas seguidas dejan la misma cantidad de filas.
- Los veterinarios sin apellido aparecen en `revision.csv` y no se cargan hasta completarlos.
- Tests con un Excel ficticio con los mismos defectos. El Excel real no está en el repositorio.

## Dependencias con otros módulos
`padron` (escrituras), y más adelante `clinica`, `cobros`, `guarderia`. Solo por sus `service.py`.

## Fuera de alcance
Corrección de datos ya cargados, fusión de duplicados posteriores (T-47) y migración continua.

## Pendientes
**Cliente:** cantidad real de filas y fecha de última edición del Excel (fecha de corte de la edad); si las deudas del Excel siguen vigentes.
**Equipo:** el mapeo de las hojas 2 y 3, cuando existan las specs de `clinica`, `cobros` y `guarderia`.
