# AGENTS.md — Huellitas

Sistema de gestión de una veterinaria de barrio con guardería canina. Resuelve cuatro problemas: padrón duplicado, historial clínico mezclado con cobros, sobreventa del cupo de guardería y deudas olvidadas.
Este archivo lo leen las personas y los agentes de IA (OpenCode). Si algo de acá contradice a un pedido ad hoc, avisá y no lo ignores en silencio.

## Fuentes de verdad

| Archivo | Qué es |
|---|---|
| `docs/specs/<modulo>.md` | La spec del módulo del ticket. **Manda sobre lo demás** para ese módulo. |
| `docs/reglas-de-negocio.md` | Catálogo de reglas (RN-xx), glosario, matriz de roles y registro de decisiones. **Leerlo antes de implementar.** |

- Si una spec y el catálogo **se contradicen**, o **falta una regla**, **parar y preguntar**.
- **No inventar reglas.** Las marcadas como `SUPUESTO` o `PENDIENTE` **no son definitivas**.
- El catálogo está cargado siempre en el contexto de los agentes (vía `instructions` en `opencode.json`). Las **specs no**: cada agente lee solo la de su módulo.

## Stack

| Capa | Tecnología |
|---|---|
| Backend | Python 3.12 + FastAPI + SQLAlchemy 2.x + Alembic |
| Base de datos | SQLite (modo WAL, `foreign_keys=ON`) |
| Frontend | React + TypeScript + Vite (mobile-first) |
| Migración de datos | Python + pandas (scripts en `backend/scripts/migracion/`) |
| Tests | pytest (backend), Vitest + Testing Library (frontend), Playwright (E2E del Hito 2) |
| Calidad | ruff + mypy (back), eslint + tsc (front) |
| CI | GitHub Actions (aún no configurado) |

El sistema corre en la PC del mostrador y se usa desde celulares por la red local. La señal es mala a veces: toda escritura crítica (pagos, reservas) debe ser idempotente y la UI tiene que tolerar reintentos.
`v0` se usa SOLO como referencia visual y **no está en este repo**: es una copia local del sistema anterior, en el equipo de cada uno. No se copia código de `v0`.

## Arquitectura: monolito modular por funcionalidad

Un módulo = una spec (`docs/specs/<modulo>.md`) = una persona responsable.

```
backend/app/
  core/            # config, db, seguridad, parámetros (compartido, sin lógica de negocio)
  modules/
    identidad/     # Agustín  — usuarios, login, roles
    padron/        # Agustín  — personas, domicilio, pacientes, titularidad, empleados/profesionales
    migracion/     # Agustín  — ingesta del Excel histórico
    cobros/        # Emiliano — cargos, pagos, señas, saldos, deudas, gastos a externos
    panel/         # Emiliano — finanzas del Dueño (solo lectura)
    guarderia/     # Aldana   — cupo, reservas, cotizador, multimascota, plaza de emergencia
    clinica/       # Aldana   — historia clínica, agenda veterinaria, adjuntos, externos
  main.py
backend/tests/     # tests de integración y de arquitectura (del proyecto entero)
backend/scripts/migracion/   # scripts de ingesta del Excel
frontend/src/
  core/            # shell, router, cliente API, estilos
  modules/<modulo>/  # misma partición que el backend
docs/specs/        # una spec por módulo
```

Dentro de cada módulo: `models.py`, `schemas.py`, `repository.py`, `service.py`, `router.py` y `tests/`.
Los tests de un módulo van en `backend/app/modules/<modulo>/tests/`. Los tests de integración y el de arquitectura van en `backend/tests/`.

**Reglas de módulo (obligatorias):**
1. Un módulo solo escribe en sus propias tablas.
2. Otro módulo solo se usa a través de su `service.py` público. Nada de importar `models.py` ni `repository.py` ajenos, ni `relationship()` entre módulos.
3. Se permiten FK a IDs de otro módulo, pero la consulta pasa por el service del dueño.
4. Un cambio que toca dos módulos se acuerda primero en la spec y se avisa al responsable del otro módulo.
5. Los routers no tienen lógica de negocio: validan, llaman al service y devuelven.
6. El frontend sigue la misma partición y no importa componentes internos de otro módulo.
7. La regla 2 también aplica a los **tests**: un test de un módulo tampoco importa `models.py` ni `repository.py` de otro módulo. Usa su `service.py` o factories propias del módulo. El test de arquitectura (`backend/tests/test_arquitectura.py`) escanea `app/` completo, `tests/` incluidos.

## Reglas de negocio que NO se negocian

### Cupo de guardería (RN-10 a RN-19)

- **RN-10** — Las franjas son **Día** y **Noche**. El "medio día" del Excel se migra como Día.
- **RN-11** — El cupo se controla **por fecha y por franja**, por separado. **Cuenta animales**: un animal ocupa **una plaza** por franja, y perros y gatos ocupan el mismo cupo. *No hay fracciones de plaza.*
- **RN-12** — Una estadía que cubre día y noche **ocupa una plaza en cada franja**. *(SUPUESTO)*
- **RN-13** — Plaza de emergencia: el cupo público es el cupo máximo **menos** las plazas de emergencia (por defecto 1, parametrizable).
- **RN-14** — Habilitar una plaza de emergencia para reserva pública requiere una **acción explícita del veterinario a cargo**, registrada con quién, cuándo, para qué fecha y franja, y el motivo. Queda auditada.
- **RN-15** — Una reserva que **supera el cupo disponible se rechaza**. La única forma de ampliarlo es RN-14. *(SUPUESTO)*
- **RN-16** — Se puede reservar **hasta 4 meses** a futuro.
- **RN-17** — Reservar en guardería **exige una seña obligatoria**, de monto libre.
- **RN-18** — Descuento automático del **20 %** sobre la tarifa diaria total cuando un mismo tutor reserva a la vez para dos o más mascotas. *(Detalles en pendientes con el cliente.)*
- **RN-19** — La tarifa depende de **la franja, la cantidad de días y los cuidados extras** (sí o no). *No de la raza ni del comportamiento.*

> **Pendiente con el cliente: el factor por tamaño del animal.** Los apuntes dicen que el cupo es de 8 a 10 "según el tamaño", pero **el cliente no confirmó** si alcanza con un número configurable o hay que calcular por tamaño. **Mientras tanto NO se implementan fracciones de plaza ni factores por tamaño**: un animal = una plaza (RN-11). Si se implementa, es una decisión nuestra y hay que registrarla como RN nueva y validarla.
> Lo mismo con el pendiente de si la plaza de emergencia es por día calendario o por franja: **no se resuelve por decreto**, se consulta.

### Padrón (RN-01 a RN-07)

- **RN-01** — El cliente nuevo se registra con DNI, nombre, apellido y teléfono. La dirección es opcional.
- **RN-02** — El DNI es **único cuando existe**. Los clientes migrados del Excel pueden no tenerlo: se completa en su próxima visita. *(SUPUESTO)*
- **RN-03** — Una mascota puede tener **más de un dueño**. Uno figura como titular y responsable de pago. *(Titular: SUPUESTO.)*
- **RN-04** — Se puede **cambiar el dueño** de una mascota y **su historia clínica se conserva**.
- **RN-05** — La especie es obligatoria: **perro o gato**.
- **RN-06** — Al crear una mascota o un dueño, el sistema **avisa** si ya existe una coincidencia (mismo dueño y nombre de mascota, o mismo teléfono) y **nunca fusiona automáticamente**.
- **RN-07** — Características y comportamiento de la mascota y del dueño van en un campo propio, **separado** de lo clínico y de los pagos.

### Cobros y deudas (RN-20 a RN-24)

- **RN-20** — Cada servicio tiene un total y **uno o más pagos** (seña, parciales, saldo). Cada pago registra monto, medio (efectivo, débito, transferencia, Mercado Pago), fecha y **el empleado que lo registró**.
- **RN-21** — La deuda se calcula como **total menos pagos**. **No se carga a mano.**
- **RN-22** — El precio **puede cambiarse hasta antes de cobrar**: se guardan el precio calculado, el precio final y el motivo. *(Guardar el motivo: SUPUESTO.)*
- **RN-23** — **La deuda NO impide** retirar la mascota ni contratar nuevos servicios. El sistema **solo muestra una alerta visible**. Restringir nuevos servicios es una decisión humana de empleados y dueño.
- **RN-24** — La seña **no es un porcentaje fijo**: varía según el servicio.

> **Registro inmutable:** una vez registrado, un asiento de cargo o de pago **no se edita**: se corrige con un asiento nuevo. Esto es compatible con RN-22, que habla del **precio previo al cobro**: ese precio sí se puede cambiar, con usuario, valor anterior y motivo.

### Clínica y personal (RN-30 a RN-33)

- **RN-30** — Cada mascota tiene **su propia historia clínica** (consultas, vacunas, cirugías, tratamientos), **separada de los pagos**.
- **RN-31** — Una cirugía (por ejemplo castración) **requiere un veterinario externo**, que **se registra con su costo**.
- **RN-32** — La agenda veterinaria funciona en un **horario acotado**. Los turnos de personal son **Mañana, Tarde y Noche**, con **30 minutos de traspaso** entre turnos.
- **RN-33** — Cada servicio registra **qué empleado o veterinario lo realizó**.

### Roles (RN-40)

- **RN-40** — Hay **tres roles**. Cada endpoint declara el rol requerido y **el default es denegar**.

| Rol | Accede | No accede |
|---|---|---|
| `DUENIO` | Todo, incluido el panel financiero y los gastos a externos | — |
| `EMPLEADO` | Padrón, reservas, cobros, deudas, turnos y guardería | Finanzas del Dueño, gastos a externos, historial clínico |
| `VETERINARIO` | Historial clínico, agenda veterinaria, los servicios que realizó | Finanzas del Dueño, gastos a externos |

> **Pendiente con el cliente:** RN-40 asigna el historial médico al veterinario clínico y lista para recepción "deudas, turnos y guardería". Si recepción necesita ver la historia clínica, hay que **confirmarlo** y actualizar RN-40. Por ahora, recepción no la ve.
> El **veterinario externo (RN-31) no es un usuario del sistema**: se registra en el servicio con su costo, no inicia sesión.

### Migración (RN-50)

- **RN-50** — **Todos** los datos del Excel se migran, **incluidas las deudas**, como saldo pendiente con origen "migración". Se **conserva el texto original** de cada registro. *(Conservar el texto: SUPUESTO.)*

### Números de negocio

- **No hardcodear el cupo.** Capacidad máxima, plazas de emergencia, descuento multimascota, anticipación máxima de reservas, anticipo y seña **viven en la tabla de configuración (`core`) o en columnas editables**, y se leen desde ahí.
- **Ningún `10`, `8`, `0.5`, `0.2`, `4` meses ni ningún otro número de negocio** en el código de negocio ni en los tests. *Los tests siembran su propia configuración* (RN-11, RN-13, RN-16, RN-17, RN-18, RN-24).
- **Dinero:** enteros en centavos o `Decimal`. **Nunca `float`.**
- **Fuera del MVP 1:** karma de clientes, WhatsApp, portal de clientes, política automatizada de cancelaciones y reportes avanzados. No se implementan, pero **no se descartan los datos** (asistencia, atrasos).

## Flujo de trabajo en Git

- Ramas: `main` (producción, solo recibe de `develop` con tag) → `develop` (integración) → `feat-<nro-ticket>-<descripcion-corta>`.
  Ejemplo: `feat-24-motor-de-cupo`. Para trabajo que no es una feature: `fix-`, `chore-`, `docs-` con el mismo patrón.
- Se crea desde `develop` y se vuelve a `develop` por Pull Request. Nunca se pushea directo a `main` ni a `develop`.
- Un PR por ticket, con al menos 1 aprobación de otra persona y CI en verde. Se hace squash merge con el título en formato Conventional Commit.
- **Conventional Commits:** `tipo(módulo): descripción en imperativo`, en minúsculas, sin punto final.
  Tipos: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`, `perf`, `build`.
  Módulos (scope): `identidad`, `padron`, `migracion`, `cobros`, `panel`, `guarderia`, `clinica`, `core`, `front`, `ci`.
  Ejemplos: `feat(guarderia): rechazar reserva que supera el cupo de la franja`, `fix(cobros): calcular saldo con seña parcial`.
  Cambio incompatible: `feat(core)!:` y un pie `BREAKING CHANGE:`.
- El número de ticket sale del issue de GitHub. Si más adelante se trackea `TICKETS.md`, el número debe coincidir con el del issue.

## Tests

- **No commitear sin correr los tests.** Antes de cada commit: `cd backend && pytest -q` y, si tocaste frontend, `cd frontend && npm test -- --run`. Si fallan, no se commitea; se arregla o se pide ayuda. Esto aplica también a los agentes.
- Todo cambio de lógica de negocio trae tests. Los de **cupo, saldos y permisos** son obligatorios y cubren los bordes: justo en el límite, uno más, franja día vs noche, plaza de emergencia, seña parcial, saldo cero.
- Los tests no dependen del orden ni de datos reales. Usan una base SQLite en memoria o temporal.
- Un bug se reproduce primero con un test que falla.

## Comandos

```bash
# backend
cd backend && python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
pytest -q && ruff check . && mypy app

# frontend
cd frontend && npm install && npm run dev
npm test -- --run && npm run lint && npx tsc --noEmit
```

## Seguridad y datos

- No se commitean secretos, `.env`, archivos `.db`, backups ni el Excel con datos reales del cliente (tiene nombres y teléfonos). Todo eso va en `.gitignore`. Para tests se usan datos ficticios.
- El Excel histórico del cliente se copia a `data/` para trabajar y es de **solo lectura**: la limpieza va en el código, nunca en el archivo.
- Las contraseñas se guardan con hash (argon2 o bcrypt). El token de sesión expira.
- La base de datos y sus copias pertenecen al cliente.

## Cómo trabajar con los agentes (OpenCode)

Los agentes están en **`.opencode/agents/` (en plural)** y se invocan con `@nombre`. La línea base de permisos está en `opencode.json`.

> ⚠️ **La carpeta singular `.opencode/agent/` NO se lee.** OpenCode v2 la ignora **sin dar error**: el agente no aparece en la lista y `--agent <nombre>` cae silenciosamente en un agente por defecto **sin ninguna restricción de permisos**. Si agregás un agente, va en `.opencode/agents/`.

| Agente | Para qué |
|---|---|
| `@spec-architect` | Escribe o revisa la spec de un módulo y verifica límites entre módulos. No escribe código. |
| `@backend-dev` | Implementa endpoints, modelos, servicios y migraciones Alembic de UN módulo. |
| `@frontend-dev` | Implementa pantallas React/TS de UN módulo, mobile-first y tolerantes a mala señal. |
| `@qa-tester` | Escribe tests de bordes (cupo, saldos, roles) y busca casos que rompen la regla. |
| `@data-migration` | Perfila y limpia el Excel, y arma la ingesta con reporte de revisión. |
| `@code-reviewer` | Revisa la rama antes del PR contra este archivo y la spec. Solo lectura. |

Reglas para todos los agentes:
1. Antes de empezar, leer este archivo y la spec del módulo (`docs/specs/<modulo>.md`). **Si no hay spec, parar y pedirla.** *(Hoy ningún módulo tiene spec: se escriben con `@spec-architect`.)*
2. Trabajar solo dentro del módulo del ticket. Si hace falta tocar otro, parar y preguntar.
3. No inventar reglas de negocio: **si la spec no lo dice, preguntar**. Lo que queda en duda va a "Pendientes del cliente" de la spec, no al código.
4. Cambios chicos: un ticket, una rama, un PR.
5. **No commitear ni pushear.** Preparan el cambio, corren los tests y **proponen** el commit; el commit lo hace una persona. Está bloqueado por permisos, no solo por instrucción. Nunca `git push --force`, ni tocar `main`/`develop`.
6. Terminar cada tarea con: **qué cambió, qué tests corrieron, qué quedó pendiente**.

## Definición de hecho (por ticket)

- [ ] Criterios de aceptación del ticket cumplidos.
- [ ] Tests nuevos pasando, y la suite completa en verde.
- [ ] Lint y tipos sin errores.
- [ ] Sin números de negocio hardcodeados.
- [ ] Spec actualizada si cambió una regla.
- [ ] PR aprobado por otra persona y commits en formato Conventional Commits.
