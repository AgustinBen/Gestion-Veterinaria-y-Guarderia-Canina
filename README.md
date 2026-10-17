# 🐾 Huellitas — Sistema Integral de Gestión Veterinaria y Guardería Canina

Proyecto desarrollado para la materia **Prácticas Pre-Profesionales 1 (PPP1)** — Licenciatura en Sistemas, Universidad Nacional de Lanús (2026).

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

```bash
cd backend
python -m venv venv
source venv/bin/activate        # En Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

La API queda disponible en `http://localhost:8000`, y la documentación interactiva en `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

La aplicación queda disponible en `http://localhost:5173` (o el puerto que indique la consola).

### Variables de entorno

Copiar `.env.example` a `.env` en cada carpeta (`backend/` y `frontend/`) y completar los valores necesarios. **Nunca subir el archivo `.env` real al repositorio.**

---
## Estructura del repositorio

```
├── backend/            
├── frontend/           
├── data-migration/     
├── docs/
│   ├── contextualizacion/
│   ├── plan-de-trabajo/
│   ├── presentacion-venta-1/
│   └── Presupuesto-y-pago/
└── README.md
```

---
## Flujo de trabajo con Git

### Ramas

- **`main`**: rama estable, solo recibe merges desde `develop` en cada entrega de Hito. Protegida contra push directo.
- **`develop`**: rama de integración activa, donde se juntan todas las features antes de pasar a `main`.
- **`feature/nombre-corto`**, **`fix/nombre-corto`**, **`docs/nombre-corto`**: ramas individuales de trabajo, creadas desde `develop`, una por tarea/Issue.

Ejemplo: `feature/abm-mascotas`, `fix/validacion-cupo-guarderia`, `docs/actualizar-der`.

### Commits — Conventional Commits

Usamos el estándar [Conventional Commits](https://www.conventionalcommits.org/es/) para todo el historial:

```
<tipo>: <descripción breve en minúsculas>

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

Ejemplos:
```
feat: agregar validación de cupo diario en reservas de guardería
fix: corregir duplicado de dueño al buscar por teléfono
docs: agregar informe de análisis de arquitecturas
```

### Pull Requests

- Todo cambio a `develop` o `main` entra por Pull Request, nunca por push directo.
- Cada PR debe vincularse a un Issue del Project (`closes #N`) cuando corresponda.
- Requiere al menos 1 aprobación de un integrante antes de mergear.

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
