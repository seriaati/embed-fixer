# Testing

Install the locked development dependencies and run the suite from the repository root:

```sh
uv sync --locked
uv run pytest
uv run pytest --cov
uv run pytest tests/test_models.py
uv run pytest tests/cogs/fixer
uv run pytest tests/ui
uv run pytest -k proxy
```

The interpreter remains the repository's pinned Python 3.12. Install ffmpeg and ffprobe for the
real animation conversion test. macOS development dependencies also include uvloop so the optional
startup import resolves during type checking. That single test skips when ffmpeg is unavailable;
CI installs it and checks both binaries before running tests.
Encoder error handling and concat generation have separate tests that do not require the binary.

## Layout

Tests follow the application package: `core/`, `cogs/`, `ui/`, and `utils/`. The large fixer cog
has its own `cogs/fixer/` directory split by URLs, delivery, events, extraction, and regressions.
Database migration tests live in `migrations/`. Top-level modules and scripts keep their tests at
the root. Reusable factories live in `support/`; shared database and translation fixtures remain
in the root `conftest.py`.

## Commit and CI checks

Install the pre-commit CLI, then enable the Git hook for each clone:

```sh
pre-commit install
pre-commit run --all-files
```

The local hook runs Ruff and the complete test suite with coverage before each commit. The pytest
hook runs once without receiving staged filenames, including for commits that only change config
or translations. It uses `uv run --locked` and the same 95% coverage gate as GitHub Actions. A test
failure or insufficient coverage blocks the commit.

The `Tests` workflow runs on pull requests targeting `main`, every push to `main` including merges,
and merge-queue check requests targeting `main`. It installs the locked dependencies and media
tools, then runs the full suite. Its job ID and check name are `tests`. The existing Mergify rule
for automatic pre-commit updates also requires this GitHub Actions check before merging.

The pytest hook is skipped only by the separate pre-commit.ci service: it needs the project's
environment and media tools, which the GitHub Actions test job prepares. pre-commit.ci continues
to run the Ruff hooks. GitHub repository rules must require the `tests` check to block manual
merges when testing fails; those remote rules are not configured by these files.

## Coverage and isolation

Coverage includes every module in `embed_fixer`, plus `run.py` and `ci.py`, and measures branches.
The coverage command fails below 95% combined statement and branch coverage. Coverage measures
execution, so assertions also check observable payloads, persisted values, error handling, and
authorization decisions.

| Area | Coverage approach |
| --- | --- |
| URLs and domain registry | Supported platforms, fix selection and rotation, tracking cleanup, spoilers, sensitive content, allow/deny lists, stable IDs |
| Persistence and migrations | Real isolated SQLite, settings JSON round trips, defaults, legacy settings, fresh databases, baseline detection, repeat startup |
| Metadata and media | Real loopback HTTP, response validation, source fallbacks, download errors, upload limits, ZIP/image fixtures, real H.264 encode and full decode |
| Message and reaction flows | Discord transport mocks, original author identity, all delivery modes, preferences, permissions, notifications, deletion, rotation and retention |
| Settings UI and commands | Real Discord UI objects, all settings routes, paging, validation, translations, import/export, reset, sponsorship and user controls |
| Runtime and maintenance | Bot startup order and shutdown, health HTTP, heartbeat, sponsors, logging, Sentry filtering, task factory and README generation |

`tests/conftest.py` supplies a fake Discord token and isolated database URI before application
imports. It clears optional service credentials and disables dotenv loading while importing modules
that load environment files. The socket guard permits only loopback IPs and Unix sockets. HTTP
fixtures redirect upstream requests to local aiohttp servers. No live Discord, social platform,
Redis, or PostgreSQL service is required.

Each database test receives a fresh context and database. Migrations additionally run against
temporary SQLite files. Mocks and settings changes are restored by pytest fixtures. Assertions for
representative URL, migration, media, UI and README regressions were also checked against temporary
in-memory mutations of the relevant production functions.

## Regression guarantees

The formerly expected failures are now ordinary passing tests. These regressions cover:

- Upload limits enforced while reading response bytes, including headerless and chunked media.
  File downloads bypass response caching so the production cached client cannot preload oversized
  bodies; unrelated metadata requests retain their cache.
- Corrupt Ugoira ZIPs, CRC failures, and invalid compressed blocks returning no conversion and
  allowing source fallback.
- Each interaction media batch tracking its own delivered message ID.
- Both custom view classes capturing errors and sending ephemeral error responses.
- Layout timeouts disabling nested controls while preserving usable link buttons.
- Guild language selection persisting under the guild ID and ignoring missing guild context.

There are no expected-failure markers accepting these defects. A recurrence fails the full-suite
commit hook and GitHub Actions gate.

## Limits

These tests do not establish live Discord delivery, current upstream API availability, Redis
integration, PostgreSQL migration compatibility, deployed container health, or Python 3.15 runtime
compatibility. Discord and Redis client boundaries are mocked. SQLite migration success does not
prove PostgreSQL behavior. Use a Discord test server and the intended database backend for those
integration checks.

Existing third-party deprecation warnings from AnyIO, discord.py and Tortoise remain visible.
