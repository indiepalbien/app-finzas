# AGENTE — Guía de arquitectura y flujo para App-Finanzas

Este documento explica la estructura propuesta del proyecto, las responsabilidades de cada directorio y un flujo claro para implementar nuevas features de forma consistente.

**Propósito**: servir de referencia para desarrolladores/colaboradores cuando añaden funcionalidades (API, ingestión automática, tareas en background, UI con HTMX, modelos y migraciones).

**Ubicación del archivo**: `AGENTE.md` (raíz del repo)

**Resumen rápido**
- **Stack**: `FastAPI` (backend), `HTMX` (frontend), `Celery` (tareas background), `SQLite` + `SQLAlchemy` (DB), `Pydantic` (validación), `Alembic` (migraciones recomendadas).
- **Objetivo**: flujos reproducibles para añadir modelos, endpoints, tareas y UI.

**Estructura de directorios sugerida**
- `backend/`: Código principal de FastAPI.
  - `backend/app.py` o `backend/main.py`: punto de arranque de la app.
  - `backend/api/`: routers y endpoints organizados por dominio (`transactions.py`, `users.py`, `accounts.py`).
  - `backend/models/`: modelos SQLAlchemy y mapeos.
  - `backend/schemas/`: modelos Pydantic para request/response.
  - `backend/services/`: lógica de negocio (p. ej. `ingest/`, `categorization/`, `exchange/`).
  - `backend/tasks/`: wrappers para Celery tasks (son llamadas desde `services` cuando aplica).
  - `backend/db/`: inicialización de sesión, engine, utilidades y migraciones (`alembic/` si se usa).
  - `backend/static/`, `backend/templates/`: assets y plantillas HTMX/Jinja.

- `frontend/` (opcional si se separa): componentes estáticos, estilos, JS ligero para interactividad.

- `services/`: integraciones externas y adaptadores (correo -> parser, Splitwise client, OCR/AI). Ejemplos:
  - `services/email_ingest/`
  - `services/splitwise/`
  - `services/ocr/`

- `tasks/` o `worker/`: configuración y definiciones de Celery (con `celery.py` y tasks agrupadas).

- `ai/`: modelos, utilitarios y pipelines para OCR y clasificación automática.

- `db/` o `migrations/`: scripts de migración (si no usas Alembic manualmente, dejar este folder para SQL exportado).

- `scripts/`: utilidades para desarrollo (seed, export, import, scripts de mantenimiento).

- `tests/`: pruebas unitarias y de integración (mirar estructura paralela a `backend/`).

- `docs/`: documentación adicional, diagramas, decisiones de diseño.

- `docker/` o `compose/`: ficheros `Dockerfile`/`docker-compose` para desarrollo/CI.

**Convenciones y prácticas**
- Cada endpoint HTTP debe usar `schemas/` (Pydantic) para validación y `models/` (SQLAlchemy) para persistencia.
- Separar la lógica de negocio de los endpoints: endpoints llaman a funciones en `services/`.
- Todas las tareas asíncronas deben implementarse como `Celery tasks` en `tasks/` y ser invocadas desde `services/`.
- Añadir tests en `tests/` por cada nueva feature (unit + integration donde aplique).
- Mantener `requirements.txt` o `pyproject.toml` actualizado con nuevas dependencias.

Guía rápida: nombrado de archivos
- Routers: `api/<domain>.py` (ej. `api/transactions.py`).
- Models: `models/<entity>.py` (ej. `models/transaction.py`).
- Schemas: `schemas/<entity>.py` (ej. `schemas/transaction.py`).

Flujo para implementar una nueva feature
1. Diseñar la entidad y el esquema de datos
   - Añadir modelo SQLAlchemy en `backend/models/`.
   - Añadir schemas Pydantic en `backend/schemas/`.
2. Añadir migración
   - Si usas Alembic: crear migración con `alembic revision --autogenerate -m "add X"` y aplicarla.
   - Si usas solo SQLite en dev, documentar cambios y mantener archivo SQL o script en `db/`.
3. Implementar la lógica en `services/`
   - Crear funciones que realicen la lógica (no mezclar con HTTP layer).
4. Crear/actualizar endpoints
   - Añadir router en `backend/api/` y registrar en el app (`include_router`).
   - Documentar inputs/outputs con `schemas`.
5. Añadir tareas background si corresponde
   - Implementar una Celery task en `backend/tasks/` y llamarla desde `services/`.
6. UI / HTMX
   - Añadir fragmentos HTMX en `backend/templates/` y endpoints que devuelvan partials.
   - Usar `hx-post`/`hx-get` para interacciones sin recarga completa.
7. Tests
   - Crear tests en `tests/` para `services/`, `api/` y tasks.
8. Actualizar docs y `requirements`/`pyproject`.

Ejemplo práctico (ingestión automática de mails VISA)
1. Modelo y schema
   - `backend/models/transaction.py`: `Transaction` con campos (`id`, `user_id`, `date`, `amount`, `currency`, `payee`, `category`, `raw_text`, `source`).
   - `backend/schemas/transaction.py`: `TransactionCreate`, `TransactionRead`.
2. Servicio de parseo
   - `services/email_ingest/parser.py`: función `parse_visa_email(raw_email) -> TransactionCreate`.
3. Celery task
   - `tasks/email_ingest.py`: `@celery.task` `process_visa_email(message_id)` que baja el mail, extrae el texto y llama a `services.email_ingest.parser` y persiste la transacción.
4. Endpoint para re-procesar/manual
   - `api/admin.py`: ruta para reintentar la ingestión o procesar emails en lote.
5. Tests
   - Tests unitarios para el parser (ejemplo: fixture con cuerpos de email) y tests de integración que invoquen la task.

Pautas para QA y CI
- Añadir job que corra `pytest` en cada PR.
- Añadir linting (`ruff`/`flake8`) y formateo (`black`).
- Opcional: job para correr checks de seguridad (dependabot, safety).

Comandos útiles (desarrollo)
```bash
# Inicializar proyecto (opcional)
uv init app-finanzas

# Crear/usar venv gestionado por uv y activar manualmente si hace falta
uv venv
source .venv/bin/activate

# Añadir dependencias (cuando necesites paquetes nuevos)
uv add fastapi uvicorn sqlalchemy pydantic celery

# Generar y sincronizar lockfile (para reproducibilidad / CI)
uv lock
uv sync

# Ejecutar la app dentro del entorno manejado por uv
uv run uvicorn backend.main:app --reload --port 8000

# Ejecutar Celery worker dentro del entorno
uv run celery -A backend.worker.celery_app worker --loglevel=info

# Ejecutar tests dentro del entorno
uv run pytest -q
```

Gestión de dependencias con `uv`

`uv` es una herramienta rápida y todo-en-uno (Astral) para manejar dependencias, entornos virtuales, scripts y herramientas. Recomendada si querés un flujo moderno y reproducible con lockfiles universales.

Instalación (macOS / Linux):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# o via Homebrew / pip si lo preferís
```

Flujos y comandos útiles (ejemplos)
- Crear/Inicializar un proyecto (opcional): `uv init <name>`
- Añadir una dependencia: `uv add <package>` (crea `.venv` y resuelve paquetes)
- Ejecutar herramientas o scripts: `uv run <command>` o `uv run script.py`
- Generar lockfile: `uv lock`
- Sincronizar entorno con lockfile: `uv sync` (o `uv pip sync <file>` para compatibilidad pip)
- Crear/activar venv: `uv venv` y luego `source .venv/bin/activate`
- Usar la interfaz `pip` de `uv` para compilar e instalar requisitos:
   - `uv pip compile requirements.in --universal --output-file requirements.txt`
   - `uv pip sync requirements.txt`

Ejemplo rápido para este proyecto (recomendado)
```bash
# Instalar uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Crear venv y añadir dependencias dev/prod
uv add fastapi uvicorn sqlalchemy pydantic celery

# Generar lock y sincronizar (para reproducibilidad en CI)
uv lock
uv sync

# Para ejecutar comandos dentro del ambiente
uv run uvicorn backend.main:app --reload --port 8000
```

Integración en CI (GitHub Actions ejemplo)
```yaml
# steps
- name: Install uv
   run: curl -LsSf https://astral.sh/uv/install.sh | sh
- name: Sync dependencies
   run: uv sync
- name: Run tests
   run: uv run pytest -q
```

Notas
- `uv` soporta instalación de múltiples versiones de Python (`uv python install`) y pin de la versión (`uv python pin 3.11`).
- `uv` puede exportar lockfiles o generar `requirements.txt` compatibles si necesitás integración con infra que espera `pip`.
- Mantener `uv.lock` (o el lockfile correspondiente) en el repo para reproducibilidad.


Cómo añadir un nuevo provider/integration (e.g., Splitwise)
1. Crear `services/splitwise/client.py` con la lógica de autenticación y llamadas.
2. Añadir un adaptador en `services/splitwise/ingest.py` que transforme la respuesta en `TransactionCreate`.
3. Añadir Celery task si necesitas sincronizaciones periódicas (`tasks/splitwise_sync.py`).
4. Añadir configuraciones en `backend/config.py` (secrets, tokens) y documentar cómo obtener credenciales.

Decisiones y notas
- Aunque SQLite está bien para prototipos/local, planear migración a Postgres para producción (lock/concurrency y migraciones más robustas).
- Usar Alembic desde el inicio para evitar problemas de sincronización de modelos.

Checklist minimal al entregar una nueva feature
- [ ] Modelos y schemas añadidos
- [ ] Migración creada y aplicada (o script en `db/`)
- [ ] Service layer implementado y testeado
- [ ] Endpoints añadidos y documentados
- [ ] Tareas Celery (si aplica) implementadas
- [ ] Tests unitarios y de integración añadidos
- [ ] Documentación breve en `docs/` o en `AGENTE.md`

---
Si querés, puedo:
- Añadir un `pyproject.toml` / `requirements.txt` inicial.
- Crear la estructura de carpetas vacías en el repo.
- Implementar un ejemplo mínimo (Transaction model + endpoint + test) para arrancar.

Fin del AGENTE.
