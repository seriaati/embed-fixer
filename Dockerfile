# First, build the application in the `/app` directory.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Disable Python downloads to use the system interpreter across both images
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Install dependencies first (this layer is cached unless lockfile changes)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Copy the application code
COPY . /app

# Install the project itself
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Then, use a final image without uv
FROM python:3.12-slim-bookworm

# It is important to use the image that matches the builder, as the path to the
# Python executable must be the same

# Create a non-root user for security
RUN groupadd --system --gid 999 appuser \
 && useradd --system --gid 999 --uid 999 --create-home appuser

WORKDIR /app

# Copy the application from the builder
COPY --from=builder --chown=appuser:appuser /app /app

# Create logs directory with correct permissions for non-root user
RUN mkdir -p /app/logs && chown -R appuser:appuser /app/logs

# Place executables in the environment at the front of the path, set env var defaults
ENV PATH="/app/.venv/bin:$PATH" \
    ENV=prod \
    DB_URI=sqlite:///data/embed_fixer.db

VOLUME [ "/data", "/app/logs" ]

# Use the non-root user to run the application
USER appuser

CMD ["python", "run.py"]