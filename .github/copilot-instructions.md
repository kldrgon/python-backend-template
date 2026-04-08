# Copilot / AI Agent Instructions for backend-template

Purpose
- Quickly orient an AI coding agent to this repository so it can make precise, minimal edits.

Big picture (architecture)
- FastAPI web application with async SQLAlchemy, dependency-injector DI containers and domain sub-containers under `app/*/container.py`.
- Domain event framework lives in `pami_temporal_event_framework` and the project uses an Outbox pattern (see `app/container.py` and `core/framework_bootstrap.py`).
- App vs worker: HTTP `app` process should NOT load domain event handlers; consumer/worker processes load handlers via `app.bootstrap.initialize_event_handlers()`.

How to run & common developer flows
- Run server (local/dev/prod): `uv run python main.py --env local|dev|prod --debug` (see README.md).
- Run tests: `make test`  (uses `ENV=test pytest tests -s`).
- Coverage: `make cov`.
- Docker compose: `docker-compose -f docker/docker-compose.yml up`.

Key project conventions (do not invent new patterns)
- Configuration: centralized in `core/config.py` via `config` facade. Read and set ENV with `ENV` environment variable (default `local`).
- Database: use `@Transactional()` (see README) — do NOT call `commit()` manually. For concurrent reads with `asyncio.gather()` use `session_factory()` context manager.
- DI: prefer wiring via `app.bootstrap.initialize_di_container()` / `app.container.Container`. Put domain wiring in `app/<domain>/container.py`.
- Event handlers: importing handler modules registers them. Only load handlers in worker/consumer processes; web API process must avoid loading heavy handlers.
- Caching: use `core.helpers.cache.Cache` decorator and `CacheTag` for tag-based invalidation.

Integration points & dependencies
- Database: async SQLAlchemy (`sqlalchemy[asyncio]`), configured in `core/config.py`.
- Message/Event systems: `pami_temporal_event_framework`, `kombu`, `aio-pika`, `temporalio` (see `pami_temporal_event_framework` and `core/config.py`).
- Blob storage: S3/MinIO related settings live in `core/config.py` (S3BlobSettings).
- Auth: JWT and custom `CurrentUser` middleware under `core/fastapi/*`; auth-related services under `app/auth`.

What to change and what to avoid
- Safe changes: add/fix API endpoints under `app/*/adapter/input/api`, small DI or service fixes, unit tests under `tests/unit_tests`.
- Avoid: changing event handler registration semantics, core framework bootstrap logic, or transactional/session internals without thorough tests and local runs.

Files to inspect for examples
- App bootstrap and DI: [app/bootstrap.py](app/bootstrap.py#L1)
- Top-level container wiring: [app/container.py](app/container.py#L1)
- Configuration facade: [core/config.py](core/config.py#L1)
- Run instructions and DB notes: [README.md](README.md#L1)

Editing guidelines for AI agents
- Make minimal, localizable patches. Prefer editing a single file per change set and update tests.
- When introducing behavior affecting DB or events, add/modify tests and include a short run instruction in the commit message (how to reproduce locally).
- If a change requires loading handlers or worker behavior, note that CI/local may need ENV change and `alembic upgrade head` for DB migrations.

If you need clarification
- Ask a single focused question and reference the target file path and function/class name.

— end —
