# First, build the application in the `/app` directory.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Disable Python downloads to use the system interpreter across both images
ENV UV_PYTHON_DOWNLOADS=0

# Build argument for optional dependencies (e.g., "pgsql")
ARG EXTRA_DEPENDENCIES=""

# Required for git-based Python dependencies during `uv sync`
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev ${EXTRA_DEPENDENCIES:+--extra} ${EXTRA_DEPENDENCIES}

# Copy the application code
COPY . /app

# Install the project itself
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev ${EXTRA_DEPENDENCIES:+--extra} ${EXTRA_DEPENDENCIES}

# Then, use a final image without uv
FROM python:3.12-slim-bookworm

WORKDIR /app

COPY --from=builder /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    ENV=prod \
    DB_URI=sqlite:///data/embed_fixer.db

VOLUME ["/data", "/app/logs"]

CMD ["python", "run.py"]