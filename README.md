# 🐾 Huellitas - Sistema Integral de Gestión Veterinaria y Guardería Canina

[![CI](https://github.com/AgustinBen/Gestion-Veterinaria-y-Guarderia-Canina/actions/workflows/ci.yml/badge.svg?branch=develop)](https://github.com/AgustinBen/Gestion-Veterinaria-y-Guarderia-Canina/actions/workflows/ci.yml)

Proyecto desarrollado para la materia **Prácticas Pre-Profesionales 1 (PPP1)** - Licenciatura en Sistemas, Universidad Nacional de Lanús (2026).

Sistema de gestión para una veterinaria de barrio que combina atención clínica (consultas, vacunas, cirugías) con servicio de guardería canina por día/noche, resolviendo los problemas de duplicación de datos, historial clínico desestructurado, sobreventa de cupos y falta de trazabilidad de cobros que hoy enfrenta el negocio.

---
## Integrantes del equipo

| Nombre                      | GitHub                                               |
| --------------------------- | ---------------------------------------------------- |
| Ledesma Rodríguez, Emiliano | [@EmiLuca](https://github.com/EmiLuca)               |
| Vallejos, Aldana            | [@AldanaVallejos](https://github.com/AldanaVallejos) |
| Bengolea, Agustín           | [@AgustinBen](https://github.com/AgustinBen)         |

---
## Stack tecnológico

| Capa                 | Tecnología                                  | Motivo                                                                                                                                                                             |
| -------------------- | ------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Backend              | Python + FastAPI                            | API rápida de construir, documentación automática (Swagger/OpenAPI), validación de datos integrada con Pydantic.                                                                   |
| Base de datos        | SQLite (+ SQLAlchemy como ORM)              | Cero configuración para desarrollo. WAL, claves foráneas y timeout de bloqueo se activan en cada conexión (`backend/app/core/db.py`). Camino de migración a PostgreSQL disponible si el proyecto lo requiere más adelante. |
| Frontend             | TypeScript + React (Vite)                   | Tipado estático para prevenir errores en equipo, ecosistema maduro de componentes. Node fijado en 20.20.2 (`frontend/.nvmrc`).                                                     |
| Migración de datos   | Python + Pandas                             | Perfilado, limpieza y estandarización del Excel histórico del cliente antes de la carga a la base definitiva.                                                                      |
| Control de versiones | Git + GitHub (Issues, Projects, Milestones) | Trazabilidad de tareas e historial de commits por integrante.                                                                                                                      |

---
## Cómo levantar el proyecto localmente

### Backend

Requisitos: Python 3.12

```powershell
cd backend
py -3.12 -m venv .venv
python -m venv .venv  # si ya es 3.12+
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item ..\.env.example .env      # y completar los valores reales
alembic upgrade head                # crea o actualiza backend/huellitas.db
uvicorn app.main:app --reload
```

> Si PowerShell bloquea la activación del entorno virtual (`ExecutionPolicy`), podés ejecutar los binarios directamente: `.venv\Scripts\pip.exe install -e ".[dev]"` y `.venv\Scripts\uvicorn.exe app.main:app --reload`. No modificamos políticas del sistema.

La API queda disponible en `http://localhost:8000`, y la documentación interactiva en `http://localhost:8000/docs`.

El esquema de la base vive en `backend/alembic/` y **no** se crea solo al arrancar la API: hay que aplicar `alembic upgrade head` después de instalar y cada vez que se baje una migración nueva. Los tests no lo necesitan, arman su propia base.

### Frontend

Requisitos: Node 20.20.2, fijado en `frontend/.nvmrc`. Si la versión instalada no coincide, `npm ci` lo avisa con `EBADENGINE`.

```powershell
cd frontend
nvm use          # o fnm use: deja Node 20.20.2
npm ci
npm run dev
```

La aplicación queda disponible en `http://localhost:5173` (o el puerto que indique la consola). Vite hace proxy de `/api` hacia `http://127.0.0.1:8000`, así que el backend tiene que estar corriendo. Para apuntar a otra API, copiar `frontend/.env.example` a `frontend/.env.local` y definir `VITE_API_URL`.

### Variables de entorno

Copiar `.env.example` (ubicado en la raíz) a `.env` en `backend/` y completar los valores necesarios. **Nunca subir el archivo `.env` real al repositorio.**

| Archivo | Variables |
| --- | --- |
| `backend/.env` | `DATABASE_URL`, `SECRET_KEY`, `SESSION_MINUTES`, `PASSWORD_MIN_LENGTH`, `UPLOADS_*` y el bootstrap del usuario Dueño (`DUENIO_USERNAME`, `DUENIO_PASSWORD`). |
| `backend/.env` (migración) | `EXCEL_ORIGEN` apunta al Excel real (por defecto `data/planilla.xlsx`) y `MIGRACION_SALIDA` a los reportes (por defecto `data/reportes`). Ninguno de los dos se versiona. |
| `frontend/.env.local` | `VITE_API_URL`. Si queda vacía se usa el proxy `/api` de Vite. |

### Migración del Excel y datos de prueba

Los scripts se corren desde `backend/` con el entorno virtual activado:

| Script | Para qué |
| --- | --- |
| `python scripts/perfilar_excel.py` | Perfilado del Excel histórico (T-15). Solo lee y reporta. |
| `python scripts/cargar_padron.py` | Carga del padrón (T-16, RN-50), con las deudas incluidas como saldo pendiente. Acepta `--simular` para correrlo sin escribir. |
| `python scripts/crear_dueno.py` | Crea el usuario Dueño inicial a partir de `DUENIO_USERNAME` y `DUENIO_PASSWORD`. |
| `python scripts/sembrar_demo.py` | Datos de demostración: tutores, mascotas, cargos y pagos. |
| `python scripts/sembrar_guarderia_demo.py` | Ocupa el cupo de guardería de hoy con las mascotas del seed anterior. |

Todos son idempotentes: se pueden volver a correr sobre la misma base. El Excel real, los reportes y la base SQLite quedan fuera del repositorio (`data/`, `*.db`).

---
## Estructura del repositorio

```
├── .githooks/            hooks versionados: commit-msg y pre-commit (ver Hooks de Git)
├── .github/workflows/    CI y validación del título de PR
├── backend/
│   ├── alembic/          migraciones de base de datos
│   ├── app/
│   │   ├── core/         configuración, base de datos, modelos base y parámetros
│   │   ├── main.py
│   │   └── modules/
│   │       ├── identidad/
│   │       ├── padron/
│   │       ├── migracion/
│   │       ├── cobros/
│   │       ├── panel/
│   │       ├── guarderia/
│   │       └── clinica/
│   ├── scripts/          perfilado y carga del Excel, seeds de demostración
│   ├── tests/
│   ├── alembic.ini
│   └── pyproject.toml
├── frontend/
│   ├── public/
│   └── src/
│       ├── core/         cliente HTTP, sesión, router, layout y estilos compartidos
│       ├── modules/      un directorio por módulo, igual que el backend
│       └── test/         setup de Vitest + Testing Library
├── docs/
│   ├── reglas-de-negocio.md   glosario y reglas RN-xx (fuente de verdad)
│   ├── specs/                 especificación por módulo
│   └── *.pdf                  documentos de la materia
├── AGENTS.md             reglas de trabajo para agentes
└── README.md
```

No se versionan: `data/` (Excel real y reportes de migración), `*.db` (base SQLite), `uploads/`, `.env` real y `node_modules/`.

---
## Flujo de trabajo con Git

### Ramas

- **`main`**: rama estable, solo recibe merges desde `develop` en cada entrega de Hito. Protegida contra push directo.
- **`develop`**: rama de integración activa, donde se juntan todas las features antes de pasar a `main`.
- **`feat-<nro>-<descripcion>`**, **`fix-<nro>-<descripcion>`**, **`chore-<nro>-<descripcion>`**, **`docs-<nro>-<descripcion>`**: ramas individuales de trabajo, creadas desde `develop`, una por tarea/Issue. No usar `feature/`.

Ejemplo: `feat-12-abm-mascotas`, `fix-15-validacion-cupo-guarderia`, `docs-03-actualizar-der`.

### Commits — Conventional Commits

Usamos el estándar [Conventional Commits](https://www.conventionalcommits.org/es/) para todo el historial:

```
<tipo>(<scope>): <descripción breve en imperativo y minúsculas>

[cuerpo opcional con más detalle]
```

**Tipos usados en este proyecto:**

| Tipo | Cuándo usarlo |
|---|---|
| `feat` | Nueva funcionalidad |
| `fix` | Corrección de un bug |
| `docs` | Cambios en documentación (README, informes, diagramas) |
| `refactor` | Cambio de código que no agrega funcionalidad ni corrige un bug |
| `test` | Agregar o corregir tests |
| `chore` | Tareas de mantenimiento (dependencias, configuración) |
| `ci` | Cambios en workflows, hooks y configuración de integración |
| `perf` | Mejora de rendimiento |
| `build` | Cambios en el sistema de build o dependencias de empaquetado |

**Scopes:** `identidad`, `padron`, `migracion`, `cobros`, `panel`, `guarderia`, `clinica`, `core`, `front`, `ci`. El scope es opcional, pero si se usa tiene que ser uno de la lista. Un cambio incompatible se marca con `!` antes de los dos puntos: `feat(core)!: ...`.

Ejemplos:
```
feat(guarderia): rechazar reservas que superan el cupo
fix(padron): corregir duplicado de dueño al buscar por teléfono
docs(core): agregar informe de análisis de arquitecturas
chore(ci): agregar hooks de git
```

### Pull Requests

- Todo cambio a `develop` o `main` entra por Pull Request, nunca por push directo.
- Cada PR debe vincularse a un Issue del Project (`closes #N`) cuando corresponda.
- El título del PR sigue Conventional Commits y el nombre de la rama sigue `<tipo>-<nro-ticket>-<descripcion>`; `.github/workflows/pr-title.yml` lo valida.
- Requiere al menos 1 aprobación de un integrante antes de mergear.
---

## Trabajo con agentes (OpenCode)

El equipo usa [OpenCode](https://opencode.ai). [`AGENTS.md`](AGENTS.md) define cómo trabajar (arquitectura por módulos, permisos, flujo de Git, tests y definición de hecho) y [`docs/reglas-de-negocio.md`](docs/reglas-de-negocio.md) es la fuente de verdad de las reglas de negocio (RN-xx): `opencode.json` lo carga como instrucción del agente. Cuando un ticket tiene spec propia en `docs/specs/`, esa spec manda para ese módulo.

## Comandos de calidad

Backend, desde `backend/`:

```powershell
cd backend
pytest -q
ruff check .
mypy app
```

Frontend, desde `frontend/`:

```powershell
cd frontend
npm test -- --run
npm run lint
npx tsc --noEmit
```

El CI (`.github/workflows/ci.yml`) corre lo mismo en cada PR y en cada push a `develop` y `main`.

## Hooks de Git

Los hooks versionados viven en `.githooks/` y se activan una sola vez por clon:

```powershell
git config core.hooksPath .githooks
```

En Git Bash también podés correr `sh scripts/setup-hooks.sh`, que hace lo mismo y ajusta los permisos de ejecución.

| Hook | Qué hace |
|---|---|
| `commit-msg` | Rechaza mensajes que no cumplen Conventional Commits, con los tipos y scopes de este repo. |
| `pre-commit` | Si hay cambios en `backend/`, corre `pytest -q`; si hay cambios en `frontend/`, corre `npm test -- --run`. Si algo falla, bloquea el commit. |

- `pre-commit` corre sobre el árbol de trabajo, no solo sobre lo que está en el índice.
- Necesita `backend/.venv` con las dependencias de dev y, para el frontend, `frontend/node_modules`.
- Para saltear los hooks: `git commit --no-verify`. No reemplazan al CI (T-04), que es la red de seguridad.
- La protección de ramas se configura en GitHub: `main` y `develop` solo reciben PR con 1 aprobación y ramas actualizadas, sin push directo ni force push, y a `main` solo se mergea desde `develop`.

## Gestión de tareas

El seguimiento de tareas se realiza en la sección **Projects** de este repositorio, organizado por:
- **Milestones**: Hito 0, Hito 1, Hito 2.
- **Tipo de tarea**: Código, Documentación, Diagrama/Modelado, Testing.

---
## Documentación del proyecto

| Documento                              | Link                                                              |
| -------------------------------------- | ----------------------------------------------------------------- |
| Glosario y reglas de negocio (RN-xx)   | [Ver documento](docs/reglas-de-negocio.md)                        |
| Especificaciones por módulo            | [Ver carpeta](docs/specs)                                         |
| Contextualización Inicial del Proyecto | [Ver documento](docs/contextualizacion.pdf)                       |
| Plan de trabajo                        | [Ver documento](docs/plan-de-trabajo.pdf)                         |
| Primera presentación de venta          | [Ver presentación](docs/presentacion-venta-1.pdf)                 |
| Presupuesto y formas de pago           | [Ver documento](docs/Presupuesto-y-pago.pdf)                      |

---
## Cronograma 

- **Hito 0** - Propuesta técnica y arquitectura (no evaluable / bloqueante).
- **Hito 1 / Parcial 1** - MVP operativo inicial: migración de datos + CRUD de entidades principales + flujo operativo básico.
- **Hito 2 / Parcial 2** - MVP completo: reglas de negocio complejas (cupos, anti-solapamiento, cuentas corrientes), reportería y control de acceso por roles.
