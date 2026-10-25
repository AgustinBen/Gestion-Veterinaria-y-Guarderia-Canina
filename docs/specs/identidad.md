# Spec: identidad

**Responsable:** Agustín · **Módulo:** `backend/app/modules/identidad/` · **Tickets:** T-10 · **Reglas:** `docs/reglas-de-negocio.md`

## Estado
Borrador v0.2 (2026-10-21). Decisión D6 cerrada (registro en la sección 6 de `docs/reglas-de-negocio.md`). Pendiente de revisión cruzada (Emiliano y Aldana).

## Objetivo
Autenticar usuarios, aplicar roles en todos los endpoints y dejar que el Dueño edite la configuración parametrizable. No gestiona personas ni empleados (eso es `padron`).

## Reglas de negocio que implementa
- **RN-40:** tres roles (`DUENIO`, `PERSONAL`, `VETERINARIO`). Las deudas están separadas de las finanzas.
- **RN-14 (solo permisos):** únicamente `VETERINARIO` o `DUENIO` habilitan la plaza de emergencia. El efecto lo implementa `guarderia`. El rol define los permisos; que alguien sea veterinario (`es_veterinario` en `padron.empleado`) es un dato aparte, necesario para los cirujanos externos que no tienen usuario.
- **Default denegar:** todo endpoint declara sus roles con `require_role`. Si no los declara, nadie accede.
- Solo `DUENIO` crea y modifica usuarios y cambia la configuración. `DUENIO` pasa en todos los endpoints.
- Sesión con vencimiento. Los minutos salen de `Settings` (variable de entorno), no del código.
- Contraseñas con hash argon2. Nunca en texto plano, en respuestas ni en logs.

## Matriz rol × recurso (PROPUESTA, ver sección 3 del catálogo)
| Recurso | DUENIO | PERSONAL | VETERINARIO |
|---|---|---|---|
| Usuarios y configuración | Sí | No | No |
| Finanzas, métricas, gastos a externos y detalle de servicios por cliente | Sí | No | No |
| Deudas y cobros | Sí | Sí | No |
| Padrón (dueños y mascotas) | Sí | Sí | Lectura |
| Reservas y cupo de guardería | Sí | Sí | Lectura |
| Habilitar plaza de emergencia | Sí | No | Sí |
| Turnos veterinarios | Sí | Sí | Sí |
| Historia clínica | Sí | Lectura (PENDIENTE CLIENTE) | Sí, con escritura |

## Entidades y campos
`usuario` (`*` = obligatorio):
| Campo | Tipo | Notas |
|---|---|---|
| id* | int, PK | autoincremental |
| username* | str(50) | único, sin distinguir mayúsculas |
| password_hash* | str | argon2 |
| rol* | enum `DUENIO`, `PERSONAL`, `VETERINARIO` | |
| activo* | bool | por defecto true |
| empleado_id | int, nulo | referencia a `padron.empleado` (la FK la agrega T-11) |
| creado_en* | datetime | |

La configuración no tiene tabla propia: usa `core.configuracion` (clave, valor, tipo `int|decimal|bool|str`, módulo, descripción). El token es un JWT firmado con `sub` (id), `rol` y `exp`; no se guarda.

## Endpoints
| Método | Ruta | Rol | Descripción |
|---|---|---|---|
| POST | /api/auth/login | público | `{username, password}` devuelve `{access_token, token_type, rol}` |
| POST | /api/auth/logout | autenticado | el cliente descarta el token (sin revocación en el servidor, SUPUESTO) |
| GET | /api/auth/me | autenticado | id, username, rol, empleado_id |
| GET | /api/usuarios | DUENIO | lista de usuarios (agregado respecto del ticket) |
| POST | /api/usuarios | DUENIO | crea usuario (username, password, rol, empleado_id opcional) |
| PATCH | /api/usuarios/{id} | DUENIO | activa o desactiva y cambia contraseña |
| GET | /api/config | DUENIO | lista los parámetros |
| PUT | /api/config/{clave} | DUENIO | cambia el valor y valida el tipo; guarda quién y cuándo |

Códigos: 401 sin token, token inválido o vencido, o usuario inactivo; 403 rol insuficiente; 404 clave de configuración inexistente; 409 username repetido; 422 datos inválidos.

## Contrato público (`identidad/service.py`)
```python
usuario_actual(db, token: str) -> UsuarioActual      # id, username, rol, empleado_id; error si el token es inválido
tiene_rol(usuario: UsuarioActual, *roles: Rol) -> bool
```
Los routers de todos los módulos protegen con la dependencia `require_role(*roles)`.

## Casos borde
- Token vencido o con firma alterada: 401.
- Usuario desactivado con token vigente: 401 (se consulta `activo` en cada pedido).
- Login con usuario inexistente, contraseña incorrecta o usuario inactivo: mismo 401 y mismo mensaje.
- El Dueño no puede desactivarse a sí mismo ni dejar el sistema sin ningún `DUENIO` activo (SUPUESTO).
- `PUT /api/config/{clave}` nunca crea claves nuevas.
- `scripts/crear_dueno.py` ejecutado dos veces no duplica el usuario.

## Criterios de aceptación
- El Dueño sembrado inicia sesión y `GET /api/auth/me` devuelve su rol.
- Matriz probada: sin token 401; `PERSONAL` o `VETERINARIO` en ruta de `DUENIO` 403; `DUENIO` en ruta de `PERSONAL` 200.
- Solo `DUENIO` crea usuarios y modifica configuración.
- La contraseña no aparece en la base ni en ninguna respuesta.
- Ningún valor de negocio escrito en el código.

## Dependencias con otros módulos
- `core`: `parametros` (`get_param`, `set_param`), `db`, `Settings`.
- `padron`: valida `empleado_id` con `padron.service.obtener_empleado`.
- Todos los módulos usan `require_role`.

## Fuera de alcance
Recuperación de contraseña, doble factor, revocación de tokens, auditoría de inicios de sesión y permisos por registro.

## Pendientes
**Cliente:** quiénes tendrán usuario y con qué rol; si `PERSONAL` puede ver la historia clínica (solo lectura).
**Equipo (menores, no bloquean T-10):** si se permite cambiar el rol de un usuario existente (hoy `PATCH` solo activa y cambia contraseña); si el logout debe revocar el token.
