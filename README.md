# 🐾 Huellitas - Sistema Integral de Gestión Veterinaria y Guardería Canina

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
| Base de datos        | SQLite (+ SQLAlchemy como ORM)              | Cero configuración para desarrollo. Se recomienda activar modo WAL para mejorar concurrencia. Camino de migración a PostgreSQL disponible si el proyecto lo requiere más adelante. |
| Frontend             | TypeScript + React                          | Tipado estático para prevenir errores en equipo, ecosistema maduro de componentes.                                                                                                 |
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
uvicorn app.main:app --reload
```

> Si PowerShell bloquea la activación del entorno virtual (`ExecutionPolicy`), podés ejecutar los binarios directamente: `.venv\Scripts\pip.exe install -e ".[dev]"` y `.venv\Scripts\uvicorn.exe app.main:app --reload`. No modificamos políticas del sistema.

La API queda disponible en `http://localhost:8000`, y la documentación interactiva en `http://localhost:8000/docs`.

### Frontend

pendiente (T-09)

La aplicación queda disponible en `http://localhost:5173` (o el puerto que indique la consola).

### Variables de entorno

Copiar `.env.example` (ubicado en la raíz) a `.env` en `backend/` y completar los valores necesarios. **Nunca subir el archivo `.env` real al repositorio.**

---
## Estructura del repositorio

```
├── backend/
│   ├── app/
│   │   ├── core/
│   │   ├── main.py
│   │   └── modules/
│   │       ├── identidad/
│   │       ├── padron/
│   │       ├── migracion/
│   │       ├── cobros/
│   │       ├── panel/
│   │       ├── guarderia/
│   │       └── clinica/
│   ├── pyproject.toml
│   └── tests/
├── frontend/
├── docs/
│   ├── contextualizacion.pdf
│   ├── plan-de-trabajo.pdf
│   ├── presentacion-venta-1.pdf
│   ├── Presupuesto-y-pago.pdf
│   └── specs/
└── README.md
```

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

El equipo usa [OpenCode](https://opencode.ai) con seis agentes especializados, cada uno con
**permisos acotados por rutas**. Las reglas de trabajo que tienen que cumplir están en
[`AGENTS.md`](AGENTS.md), que OpenCode lee solo al abrir el repo.

## Comandos de calidad

Los comandos de calidad se corren desde `backend/`:

```powershell
cd backend
pytest
ruff check .
mypy app
```

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
| Contextualización Inicial del Proyecto | [Ver documento](docs/contextualizacion.pdf)                       |
| Plan de trabajo                        | [Ver documento](docs/plan-de-trabajo.pdf)                         |
| Primera presentación de venta          | [Ver presentación](docs/presentacion-venta-1.pdf)                 |
| Presupuesto y formas de pago           | [Ver documento](docs/Presupuesto-y-pago.pdf)                      |

---
## Cronograma 

- **Hito 0** - Propuesta técnica y arquitectura (no evaluable / bloqueante).
- **Hito 1 / Parcial 1** - MVP operativo inicial: migración de datos + CRUD de entidades principales + flujo operativo básico.
- **Hito 2 / Parcial 2** - MVP completo: reglas de negocio complejas (cupos, anti-solapamiento, cuentas corrientes), reportería y control de acceso por roles.
