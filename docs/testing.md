# Testing

Use Python 3.15, matching `.python-version`, package metadata, Ruff, Pyrefly, CI, and Docker.
Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and the locked dependencies:

```sh
uv sync --locked
```

Install ffmpeg and ffprobe before running the suite. On macOS, use `brew install ffmpeg`.
On Debian or Ubuntu, use `apt-get install ffmpeg`. The ffmpeg package supplies ffprobe.
CI installs these tools before running checks.
The media conversion test creates real image frames, writes a ZIP, converts it with ffmpeg,
and checks the resulting video with ffprobe.

## Commands

```sh
uv run --locked pytest
uv run --locked pytest tests/test_models.py
uv run --locked pytest tests/cogs/fixer
uv run --locked pytest --cov
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pyrefly check
uv run --locked pre-commit validate-config
docker buildx bake --file docker-bake.hcl
```

Coverage measures statements and branches across `embed_fixer`, `run.py`, `ci.py`, and migrations.
The coverage command fails below 95%. Tests do not exclude application error paths or optional
integrations from the report. Run `uv run --locked pytest --cov --cov-report=html` to inspect gaps.

Install the local hook with `uv run --locked pre-commit install`. Run it without committing using
`uv run --locked pre-commit run --all-files`. Its test hook runs the whole suite with coverage
once, regardless of the number of changed files. The GitHub Actions Checks workflow runs lint,
format, type, and coverage checks on Linux ARM64 and native macOS ARM64.
The Docker Build workflow calls those checks for pull requests and main pushes that change
runtime code, translations, migrations, dependencies, Docker definitions, or its build/check
workflows. Release tags and manual runs also trigger it. Images build after both platforms pass.
Documentation-only and test-only changes skip Docker builds; the dedicated Tests workflow still runs.

The Ruff hooks use their pinned isolated environment. Pyrefly and pytest use the project's locked
environment. pre-commit.ci runs Ruff and skips the local project and Docker hooks because it
cannot install their dependencies at hook runtime; GitHub Actions runs the complete gate.

The dedicated `Tests` workflow also keeps the existing `tests` check on Linux ARM64 for pull
requests, main pushes, and merge-queue requests. The Mergify rule continues to require that check.

## Container builds

`docker-bake.hcl` defines the default and PostgreSQL (`asyncpg`) variants, both targeting
`linux/arm64`. The pre-commit `docker-build` hook runs `docker buildx bake --file docker-bake.hcl`
once per commit using the selected Buildx builder. Run that command directly or use
`uv run --locked pre-commit run docker-build --all-files` to run only the build hook.

Local builds require a running ARM64 Docker engine with Buildx, such as Docker Desktop on
Apple silicon. The first run downloads base images and dependencies; later runs reuse the
builder cache. CI builds both variants on native Linux ARM64 runners after checks pass.

| Runner | Native platform | Checks |
| --- | --- | --- |
| `ubuntu-24.04-arm` | Linux ARM64 | Tests, lint, types, both Docker variants |
| `macos-26` | macOS ARM64 | Tests, lint, types |

These use the [documented runner architectures](https://docs.github.com/en/actions/reference/runners/github-hosted-runners).
macOS tests run directly on Apple silicon; container images always use Linux.

Local and PR builds retain results in the build cache without publishing or loading images into
the Docker image store. PRs do not log in to GHCR. Main and `v*` release builds publish each
ARM64 variant directly to its image tags after both platforms' checks pass.
Manual runs publish only when run on main or a `v*` tag. Existing image tag suffixes are preserved.

## Layout and isolation

| Location | Behavior covered |
| --- | --- |
| `tests/core` | Configuration, translation, command errors |
| `tests/cogs/fixer` | Tracking cleanup, discovery, extraction, delivery, reactions, author lookup, commands |
| `tests/cogs` | Settings, administration, information, sponsors, heartbeat |
| `tests/ui` | Real Discord controls, callbacks, persisted settings, pagination, error handling |
| `tests/utils` | URL handling, provider HTTP contracts, downloads, conversion, sponsor checks, logging |
| `tests/migrations` | Real SQLite migration chains, legacy baselines, repeated startup |
| `tests/test_*.py` | Models, registry, bot lifecycle, health endpoint, executable startup |
| `tests/support` | Shared Discord transport factories |

The root fixtures load test configuration before application imports. Each database fixture
creates and closes an isolated in-memory SQLite database; migration tests use temporary files.
No test connects to the configured application database.

Pytest blocks external sockets and allows only loopback hosts and local Unix sockets. HTTP
fixtures serve real responses on an ephemeral loopback port. Provider tests route requests to
those servers while checking the original URL, request headers, and response parsing. Discord
transport calls use test doubles; UI components and settings persistence remain real.

## Tracking cleanup regressions

Tests cover platform-specific and global trackers, encoded names, repeated fields, exact retained
encoding, fragments, timestamps, playlists, selected images, and idempotence. Fixer cases cover
the default setting, persisted opt-out, source/original buttons, nested provider URLs, rotation,
spoilers, invalid URLs, and URLs opted out with `$` or angle brackets.

## Limits

Live Discord permissions, webhook delivery, provider uptime, and actual Discord embed rendering
still require server testing. The suite checks the bot's transport payloads and provider contracts.
PostgreSQL migration execution, real Redis and Sentry services, and the Linux container image
require separate environment checks; the local suite does not claim to exercise them.

Current dependencies emit deprecation warnings for Tortoise primary-key aliases,
discord.py's `asyncio.iscoroutinefunction`, and the AnyIO pytest plugin's `CallSpec2` import.
These warnings remain visible. An empty coverage branch in fix rotation is also visible because
the loop assigns its first domain and immediately exits.

The Docker images use the Python 3.15 Trixie tags listed in the
[official uv Docker guide](https://docs.astral.sh/uv/guides/integration/docker/).
The Linux event-loop dependency requires the Python 3.15 wheels introduced in
[uvloop 0.23.0](https://github.com/MagicStack/uvloop/releases/tag/v0.23.0).
