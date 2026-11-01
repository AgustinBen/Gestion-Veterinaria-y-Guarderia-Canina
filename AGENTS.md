# AGENTS.md — HUELLITAS | LECTURA OBLIGATORIA

> LEER ANTES DE HACER CUALQUIER COSA. Si hay conflicto con un pedido ad-hoc, seguir este archivo.
> Todo lo que antes figuraba como `PROPUESTA` o `SUPUESTO` pasa a ser **DECIDIDA** y **OBLIGATORIA**.

## 1. FUENTES DE VERDAD

| Archivo | Uso |
| --- | --- |
| `docs/reglas-de-negocio.md` | **OBLIGATORIO.** Glosario, RN-xx, matriz de roles y decisiones. Leer SIEMPRE. |
| `docs/specs/<modulo>.md` | **MANDA para ese módulo.** Si existe, prevalece para ese ticket. |
| `AGENTS.md` | Guía transversal para todo el proyecto. |

- **NO INVENTAR REGLAS.** Si no está escrito, preguntar.
- **Excel en `data/` es SOLO LECTURA.** La limpieza va en código.

## 2. STACK Y ARQUITECTURA

**Stack:** Python 3.12 + FastAPI + SQLAlchemy 2.x + Alembic (SQLite WAL), React + TypeScript + Vite (mobile-first), pandas para migración. Tests: pytest / Vitest + RTL. Calidad: ruff/mypy/eslint/tsc.

**Módulos:** `identidad`, `padron`, `migracion`, `cobros`, `panel`, `guarderia`, `clinica`. Estructura backend por módulo: `models.py`, `schemas.py`, `repository.py`, `service.py`, `router.py`, `tests/`. Frontend con misma partición en `frontend/src/modules/<modulo>/`.

**REGLAS DE MÓDULO (INQUEBRANTABLES):**

1. **Aislamiento:** Un módulo solo escribe en sus propias tablas.
2. **Consumo cruzado:** Solo vía `service.py` público. **PROHIBIDO** importar `models.py` o `repository.py` ajenos. **PROHIBIDO** `relationship()` entre módulos.
3. **FKs:** Se permiten, pero la consulta debe ir por el `service.py` del dueño.
4. **Doble toque:** Si toca dos módulos → acordar en la spec que existe (no crear nuevas) y avisar al responsable **ANTES** de implementar.
5. **Router sin lógica:** Valida, llama al service, devuelve. Nada de reglas de negocio.
6. **Frontend aislado:** No importar componentes internos de otro módulo. Consumir por API/capa de servicios.
7. **Tests aislados:** No importar `models.py`/`repository.py` ajenos. Usar `service.py` o factories propias. `backend/tests/test_arquitectura.py` valida todo.
8. **Un ticket = un módulo.** Si es imprescindible tocar otro → **PARAR Y PREGUNTAR**.

## 3. REGLAS DE NEGOCIO CLAVE

### Roles (RN-40)
**Tres roles:** `DUENIO`, `PERSONAL` (recepción), `VETERINARIO`. **Default = DENEGAR**. Cada endpoint debe declarar su rol.

| Recurso | Dueño | Personal | Veterinario |
| --- | --- | --- | --- |
| Usuarios/configuración | Sí | No | No |
| Panel/finanzas/gastos a externos | Sí | No | No |
| Deudas y cobros | Sí | Sí | No |
| Listado global de deudores | Sí | No | No |
| Padrón | Sí | Sí | Solo lectura |
| Reservas/cupo guardería | Sí | Sí | Solo lectura |
| Habilitar plaza de emergencia | Sí | No | Sí |
| Turnos | Sí | Sí | Sí |
| Historia clínica | Sí | Solo lectura (a confirmar) | Sí (escritura) |

### Guardería (RN-10 a RN-19)
- **Franjas:** Día/Noche. "Medio día" del Excel → Día.
- **Cupo:** Por fecha y franja. **1 plaza/animal**. Perros y gatos comparten cupo. **Tamaño NO interviene. Sin fracciones.**
- **Día+Noche:** Ocupa **1 plaza en cada franja**.
- **Plaza de emergencia:** Cupo público = cupo máx - emergencias (1 por defecto). Solo habilitable con **acción explícita** de `VETERINARIO` o `DUENIO`, con **quién/cuándo/fecha/franja/motivo** auditado.
- **Reserva:** Si supera cupo → **RECHAZAR**. Solo se amplía por RN-14 o subiendo cupo máx.
- **Anticipación:** Máx **4 meses**.
- **Seña:** **Obligatoria**, monto libre.
- **Multimascota:** **20%** de descuento sobre tarifa diaria total si el **mismo tutor** reserva **a la vez** 2+ mascotas.
- **Tarifa:** Solo por franja, días y cuidados extras (sí/no). **No** por raza/comportamiento.

### Padrón (RN-01 a RN-09)
- **Alta:** DNI, nombre, apellido, teléfono. Dirección opcional.
- **DNI:** Único **si existe**. Si ya existe → **BLOQUEA** el alta. Migrados sin DNI se completan después.
- **Dueños:** Pueden ser varios. Debe haber **titular principal y responsable de pago**.
- **Cambio de dueño:** Se permite. **Historia clínica se conserva**.
- **Especie:** **Obligatoria** perro o gato.
- **Duplicados:** Teléfono repetido o nombre parecido **AVISAN** y exigen **confirmación explícita registrada**. **NUNCA fusionar automáticamente**.
- **Datos extra:** Características/comportamiento en campo separado de clínico/pagos.
- **Empleado migrado sin apellido:** Debe completarse antes de cargarlo.
- **Fecha nacimiento aprox:** Guardar. **Edad se CALCULA, nunca se guarda**.

### Cobros y deudas (RN-20 a RN-24)
- **Pagos:** Total + uno o más pagos. Cada pago: monto, medio (efectivo/débito/transferencia/Mercado Pago), fecha y **empleado que lo registró**.
- **Deuda:** `total - pagos`. **Se CALCULA. NO se carga a mano.**
- **Precio:** Puede ajustarse **hasta antes del pago total**. No puede quedar menor a lo ya pagado. Guardar **precio anterior, nuevo, motivo y usuario**. **Asientos no se editan:** corregir con un nuevo asiento.
- **Bloqueos:** **La deuda NO impide** retirar mascota ni contratar nuevos servicios. **Solo mostrar alerta visible**. Bloquear es decisión humana.
- **Seña:** **No es porcentaje fijo.** Varía según el servicio.

### Clínica (RN-30 a RN-33)
- **Historia clínica:** Propia por mascota, **separada de pagos**.
- **Cirugía:** Requiere **veterinario externo**. Registrar **con su costo**. **Sin usuario** en el sistema.
- **Agenda:** Horario acotado. Turnos **Mañana/Tarde/Noche** con **30 min de traspaso**.
- **Auditoría:** Cada servicio registra **quién lo realizó**.

### Migración (RN-50)
- **TODO el Excel:** Incluidas las deudas como saldo pendiente con origen `"migración"`. **Conservar texto original**. Idempotente. Escribir vía `service.py` de los módulos dueños, nunca vía `models/repository` ajenos.

### Técnicas
- **Sin números de negocio hardcodeados:** Cupo, emergencias, descuento, anticipación, seña/anticipo van en **configuración (`core`) o columnas editables**. **Los tests SIEMBRAN su propia config**. **PROHIBIDO** `10`, `8`, `0.5`, `0.2`, `4` en lógica de negocio/tests.
- **Dinero:** **Enteros en centavos o `Decimal`**. **NUNCA `float`**.
- **Idempotencia:** Obligatoria en pagos, reservas y habilitación de plaza de emergencia.
- **Auditoría:** Quién realizó, ajustes de precio, habilitación de emergencia, confirmaciones de duplicados.
- **Fuera MVP 1:** Karma, WhatsApp, portal de dueños, cancelaciones automáticas, reportes avanzados. No implementar.

## 4. GIT, TESTS Y COMANDOS

**Git:** `main` ← `develop` ← `feat-<nro-ticket>-<desc>`. Crear desde `develop`, volver por **PR**. **Nunca push directo a main/develop.** **Nunca `git push --force`.** 1 PR por ticket, mínima 1 aprobación, CI verde. **Squash merge** con **Conventional Commits**: `tipo(módulo): descripción en imperativo`. Tipos: `feat, fix, docs, refactor, test, chore, ci, perf, build`. Scopes: `identidad,padron,migracion,cobros,panel,guarderia,clinica,core,front,ci`. Breaking: `feat(core)!:` + `BREAKING CHANGE:`. Ticket = issue de GitHub.

**Tests:** **NO COMMITEAR SIN CORRERLOS.** Obligatorios para lógica de negocio. Cubrir **cupo, saldos, permisos** y bordes. Bug → **test que falle primero**. No modificar tests para pasar si el código está mal. Tests independientes, sin datos reales.

**Comandos:**

```bash
# Backend
cd backend && python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"
alembic upgrade head && uvicorn app.main:app --reload
pytest -q && ruff check . && mypy app

# Frontend (si tocado)
cd frontend && npm install && npm run dev
npm test -- --run && npm run lint && npx tsc --noEmit
5. CÓMO TRABAJAR
ANTES DE EMPEZAR:
1. Leer AGENTS.md, docs/reglas-de-negocio.md y docs/specs/<modulo>.md. Si no hay spec → CONTINUAR SIN SPECS.
2. Identificar módulo, RN aplicables y criterios de aceptación.
3. Verificar si toca otro módulo. Si sí → PARAR Y PREGUNTAR.
DURANTE:
- Solo tu módulo. Seguir arquitectura estricta.
- Backend: lógica SOLO en service.py. router.py sin negocio.
- Frontend: mobile-first, tolerante a mala señal (cargando/vacío/error/datos), escrituras idempotentes, validar UX pero confiar en el backend, deuda SOLO alerta (nunca bloqueo), sin valores hardcodeados.
- Migración: Excel SOLO LECTURA, idempotente, via service.py ajenos, reportar dudosos.
- Revisión: solo lectura, con archivo/línea, caso concreto, RN y propuesta de fix.
ANTES DE PROPONER COMMIT (OBLIGATORIO):
- Backend tocado: Correr pytest -q && ruff check . && mypy app y PEGAR SALIDA LITERAL.
- Frontend tocado: Correr npm test -- --run && npm run lint && npx tsc --noEmit y PEGAR SALIDA LITERAL.
- Migración tocado: Lo anterior + reporte (leídas/insertadas/actualizadas/omitidas/duplicadas + casos dudosos).
- Si no se puede correr: Decirlo explícitamente. NO decir que pasa.
AL TERMINAR (SIEMPRE):
1. Qué cambió + RN-xx o criterio de aceptación
2. Qué tests corrieron + salida literal
3. Qué quedó pendiente
4. Mensaje de commit propuesto (tipo(módulo): ...) + archivos tocados
5. Estado: Listo para que UNA PERSONA haga commit/push. TÚ NO COMMITEAS NI PUSHEAS.
6. DEFINICIÓN DE HECHO
- Criterios de aceptación cumplidos
- Reglas/RN aplicables respetadas
- Tests nuevos + suite completa en verde
- Lint + tipos sin errores
- Sin números de negocio hardcodeados
- Aislamiento de módulos respetado
- Dinero con Decimal/centavos
- Permisos correctos (rol + default denegar)
- Escrituras críticas idempotentes si aplica
- Spec actualizada si cambió una regla
- PR listo con Conventional Commits