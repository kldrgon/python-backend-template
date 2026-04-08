FROM astral/uv:python3.12-bookworm-slim AS base

WORKDIR /app

# Copy project metadata first for better layer caching
COPY pyproject.toml uv.lock ./

# Install project dependencies into a local .venv managed by uv
RUN uv sync --frozen --no-dev

# Copy the application source
COPY ./app ./app
COPY ./core ./core
COPY ./pami_event_framework ./pami_event_framework
COPY ./scripts ./scripts
COPY ./migrations ./migrations
COPY ./alembic.ini ./alembic.ini
COPY ./main.py ./main.py
COPY ./workflow_launcher.py ./workflow_launcher.py
COPY ./worker.py ./worker.py
COPY ./outbox_beat.py ./outbox_beat.py
COPY ./allinone.py ./allinone.py

EXPOSE 8000

ENTRYPOINT ["uv", "run", "--"]
CMD ["python", "main.py", "--env", "prod"]
