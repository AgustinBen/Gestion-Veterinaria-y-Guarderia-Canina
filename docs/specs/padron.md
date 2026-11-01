# Spec: padron

**Responsable:** Agustín · **Módulo:** `backend/app/modules/padron/` · **Tickets:** T-11, T-12, T-13, T-14, T-36 · **Reglas:** `docs/reglas-de-negocio.md`

## Estado
Borrador v0.2 (2026-10-21). Decisiones D1 a D14 cerradas (registro en la sección 6 de `docs/reglas-de-negocio.md`). Donde el DER y el ticket difieren, se siguió el ticket. Pendiente de revisión cruzada (Emiliano y Aldana), sobre todo del contrato público.

## Objetivo
Padrón único de personas (dueños y empleados) y mascotas, sin duplicados, con varios titulares por mascota y cambio de titular conservando el historial. Lo consumen `cobros`, `guarderia`, `clinica` y `migracion`.

## Reglas de negocio que implementa
- **RN-01** El alta de un cliente nuevo exige DNI, nombre, apellido y teléfono. La dirección es opcional. El router lo exige; `crear_persona(..., migrado=True)` permite omitir el DNI.
- **RN-02** El DNI es único cuando existe. Un DNI repetido **bloquea** el alta. Se guarda solo con dígitos.
- **RN-03 / RN-04** Una mascota tiene uno o más titulares y uno es el principal. Se puede cambiar de titular sin perder el historial.
- **RN-05** La especie es obligatoria (perro o gato).
- **RN-06** Teléfono repetido o nombre parecido **avisan** y exigen una confirmación explícita, que queda registrada. Nunca se fusiona automáticamente.
- **RN-08** Nombre y apellido son obligatorios. **RN-09** Se guarda la fecha de nacimiento aproximada y la edad se calcula.
- Cada animal ocupa 1 plaza. El padrón no guarda factor de cupo y el tamaño no interviene en el cupo (D14).

## Entidades y campos (`*` = obligatorio)
| Entidad | Campos |
|---|---|
| persona | id* PK; nombre str(50)*; apellido str(50)*; dni str(10) único, nulo; domicilio_id FK, nulo; creado_en datetime*; creado_por int, nulo (id de usuario, sin FK entre módulos); duplicado_confirmado bool* (por defecto false) |
| domicilio | id*; calle str(100); numero int; piso str(10); departamento str(10); localidad str(60); codigo_postal str(10); referencia str(150). Todos nulos salvo id. `referencia` guarda el texto original de la migración. Varias personas pueden apuntar al mismo domicilio. Al cargarlo desde la pantalla, calle y localidad son obligatorias (SUPUESTO; la migración queda exenta) |
| telefono | id*; persona_id FK*; numero_normalizado str(15)*; numero_original str(30)*. Único por (persona_id, numero_normalizado). El mismo número puede estar en varias personas |
| cliente | persona_id PK/FK*; email str(254), nulo |
| empleado | persona_id PK/FK*; tipo enum `INTERNO`/`EXTERNO`*; es_veterinario bool*; especialidad str(45), nulo; email str(254), nulo; activo bool* |
| especie | id*; nombre str(45)* único. Datos iniciales: Perro, Gato |
| raza | id*; nombre str(45)*; especie_id FK*. Único por (especie_id, nombre) |
| tamanio | id*; nombre str(45)* único. Datos iniciales: Chico, Mediano, Grande. Dato descriptivo, sin factor de cupo |
| paciente | id*; nombre str(100)*; especie_id FK*; raza_id FK, nulo; tamanio_id FK, nulo; peso_kg decimal(5,2), nulo; fecha_nacimiento_aprox date, nulo; castrado bool, nulo; activo bool*. La edad no se guarda: se calcula al leer |
| tipo_contacto | id*; nombre str(45)* único. Datos iniciales: TITULAR, CONTACTO ALTERNATIVO |
| titularidad | id*; paciente_id FK*; persona_id FK*; tipo_contacto_id FK*; principal bool*; desde date*; hasta date, nulo (nulo = vigente) |

**Reglas de titularidad**
- Un solo principal vigente por paciente (índice único parcial), y solo con tipo TITULAR.
- Siempre hay al menos un titular vigente: no se puede quitar el último.
- La primera titularidad de una mascota es siempre principal.
- Para quitar al principal primero hay que designar otro principal entre los titulares vigentes.
- Cambio de titular: se cierra la fila vigente (`hasta` = fecha del cambio) y se abre otra. El historial clínico no se toca, porque apunta a `paciente_id`.
- Una persona no puede figurar dos veces vigente en la misma mascota.

**Razas:** el formulario sugiere las existentes (comparación sin tildes ni mayúsculas) antes de crear una nueva con alta rápida.

**Normalización de teléfono (una sola función, en `padron`).** Solo dígitos; se quita el 54 inicial, luego el 9 de móvil, el 0 inicial y el 15 de móvil; si quedan 8 dígitos se antepone `codigo_area_defecto` (parámetro del módulo). Resultado: 10 dígitos. Si no se puede resolver, la API responde 422 y la migración lo manda a revisión. Ejemplos en `migracion.md`.

**Búsqueda:** texto sin tildes ni mayúsculas sobre nombre, apellido, DNI, teléfono normalizado y nombre de la mascota.

## Endpoints (roles: D = DUENIO, P = PERSONAL, V = VETERINARIO)
| Método | Ruta | Rol | Descripción |
|---|---|---|---|
| GET | /api/personas | D, P, V | búsqueda paginada (`q`, `dni`, `telefono`) |
| POST | /api/personas | D, P | alta. DNI repetido: 409 sin opción de confirmar. Teléfono repetido o nombre parecido: 409 con `coincidencias`; se repite con `confirmar_duplicado=true` y queda registrado |
| GET / PATCH | /api/personas/{id} | D, P, V / D, P | ficha, con teléfonos y domicilio / modificación |
| PUT | /api/personas/{id}/telefonos | D, P | reemplaza la lista de teléfonos |
| GET | /api/pacientes | D, P, V | búsqueda paginada |
| POST | /api/pacientes | D, P | alta; exige un titular principal |
| GET / PATCH | /api/pacientes/{id} | D, P, V / D, P | ficha, con edad calculada / modificación |
| GET | /api/pacientes/{id}/titulares | D, P, V | vigentes; `historial=true` incluye las cerradas (T-13) |
| POST | /api/pacientes/{id}/titulares | D, P | agrega titular o contacto; devuelve `TitularVigente` (T-13) |
| DELETE | /api/pacientes/{id}/titulares/{persona_id} | D, P | cierra la vigencia; 204 (T-13) |
| DELETE | /api/titulares/{titularidad_id} | D, P | alias por id de titularidad; cierra la vigencia; 204 (T-13) |
| POST | /api/pacientes/{id}/titular-principal | D, P | designa otro principal entre los vigentes (T-13) |
| POST | /api/pacientes/{id}/transferencia | D, P | cambio de titular; acepta `de_persona_id`; también `/transferir` como alias (T-13) |
| GET | /api/empleados | autenticado | lista |
| POST / PATCH | /api/empleados | D | alta / modificación |
| GET | /api/especies, /api/razas, /api/tamanios | autenticado | catálogos |
| POST | /api/razas | D, P | alta rápida de raza |

## Contrato público (`padron/service.py`)
Todas reciben `db: Session` primero. Los DTO son clases de `schemas.py`. `empleado_id` es el `persona_id` del empleado.
```python
# Lecturas (cobros, guarderia, clinica)
buscar_personas(db, texto: str | None = None, dni: str | None = None, telefono: str | None = None, limite: int = 20) -> list[PersonaResumen]
buscar_pacientes(db, texto: str | None = None, limite: int = 20) -> list[PacienteResumen]  # AGREGADO para GET /api/pacientes
obtener_persona(db, persona_id: int) -> PersonaDetalle | None
obtener_paciente(db, paciente_id: int) -> PacienteDetalle | None      # especie, raza, tamaño, peso, edad calculada. Sin factor_cupo
obtener_pacientes(db, ids: list[int]) -> dict[int, PacienteDetalle]    # fichas por lote, omite IDs inexistentes
titulares_vigentes(db, paciente_id: int) -> list[TitularVigente]     # id, persona_id, nombre, tipo, principal, desde, hasta (nulo = vigente)
titulares_historial(db, paciente_id: int) -> list[TitularVigente]    # T-13: incluye cerradas
obtener_empleado(db, empleado_id: int) -> EmpleadoDetalle | None
pacientes_de_persona(db, persona_id: int) -> list[PacienteResumen]   # AGREGADO, a validar con Aldana (multimascota)
obtener_personas_resumen(db, ids: list[int]) -> dict[int, PersonaResumen]   # AGREGADO para T-21 (listado de deudores, lectura por lote sin N+1)
# Escrituras (routers y migracion)
crear_persona(db, datos: PersonaNueva, *, confirmar_duplicado: bool = False, migrado: bool = False) -> PersonaDetalle   # lanza DniDuplicado o PosibleDuplicado(coincidencias)
crear_paciente(db, datos: PacienteNuevo, titular_persona_id: int) -> PacienteDetalle
agregar_titular(db, paciente_id: int, persona_id: int, tipo_contacto_id: int | None = None, *, principal: bool = False, usuario_id: int | None = None, fecha: date | None = None) -> TitularVigente   # T-13
quitar_titular(db, titularidad_id: int, *, usuario_id: int | None = None, fecha: date | None = None) -> None                                      # T-13
quitar_titular_de_persona(db, paciente_id: int, persona_id: int, *, usuario_id: int | None = None, fecha: date | None = None) -> None             # T-13
cambiar_principal(db, paciente_id: int, persona_id: int, *, usuario_id: int | None = None) -> TitularVigente                                       # T-13
transferir_paciente(db, paciente_id: int, nueva_persona_id: int, fecha: date | None = None, *, de_persona_id: int | None = None, tipo_contacto_id: int | None = None, usuario_id: int | None = None) -> TitularVigente   # T-13
```

## Casos borde
- Persona sin DNI: el router la rechaza; solo entra con `migrado=True`.
- Mismo DNI en otra persona: 409, no se puede confirmar. DNI con puntos o espacios: se guarda solo con dígitos.
- Dos personas con el mismo teléfono: se permite con confirmación explícita registrada.
- Quitar el último titular, quitar al principal sin designar otro, o dejar dos principales: 409.
- Transferir a quien ya es titular vigente: 409.
- Mascota sin raza o sin tamaño: válido. Mascota sin especie: 422.

## Criterios de aceptación
- Alta con DNI repetido responde 409 y no crea nada. Alta con teléfono o nombre repetido responde 409 con candidatos, y se crea solo con la confirmación.
- Una mascota puede tener dos titulares, y la transferencia conserva el historial.
- Siempre queda exactamente un principal vigente: designar otro lo cambia sin sacar titulares, y quitar al principal sin reemplazo responde 409.
- Los teléfonos de ejemplo de `migracion.md` se normalizan al valor esperado.
- Ningún campo ni función menciona `factor_cupo`.
- Los consumidores usan solo `padron/service.py` (lo verifica el test de arquitectura).
- La pantalla Dueños y mascotas muestra el rótulo “Padrón de clientes” y pagina las mascotas registradas en grupos de cinco.

## Dependencias con otros módulos
Usa `core` e `identidad` (`require_role`). Lo consumen `cobros` (titulares), `guarderia` (paciente, titulares, `pacientes_de_persona`), `clinica` (paciente, empleado), `identidad` (empleado) y `migracion` (escrituras).

## Fuera de alcance
Notas de comportamiento (T-36), fusión de duplicados (T-47), fotos, historial de cambios de datos personales y baja de personas.

## Pendientes
**Cliente:** DNI de los clientes migrados; si los contactos alternativos requieren DNI; cantidad real de filas del Excel; fecha de corte para calcular la edad.
**Equipo:** ninguno. Decisiones D1 a D14 cerradas.
