# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Stack

Python 3.12 Discord bot using `discord.py` (AutoShardedBot), Tortoise ORM, Pydantic v2, `uv` package manager, `loguru` for logging, Sentry for error tracking.

## Commands

```bash
uv run run.py                  # Start the bot
uv run ruff check --fix .      # Lint with auto-fix
uv run ruff format .           # Format
uv run pyright                 # Type check
```

No automated test suite — test manually in a Discord server.

## Environment Variables (`.env`)

- `DISCORD_TOKEN` — required
- `DB_URI` — defaults to `sqlite://embed_fixer.db` (PostgreSQL supported via `asyncpg` optional dep)
- `ENV` — `dev` or `prod` (health cog skipped in `dev`)
- `REDIS_URL`, `SENTRY_DSN`, `PROXY_URL`, `HEARTBEAT_URL` — optional

## Critical Patterns

### Settings Model (non-obvious architecture)

`GuildSettings` and `UserSettings` are **Pydantic models**, NOT Tortoise ORM models. They are stored as JSON blobs in `SettingsTable` (Tortoise). Always use the Pydantic class methods:

```python
settings, created = await GuildSettings.get_or_create(guild_id)
settings = await GuildSettings.get_or_none(guild_id)
await settings.save()
```

Never query `GuildSettingsTable` directly for settings — use the Pydantic wrapper.

### URL Helpers (use these, not str methods)

```python
from embed_fixer.utils.misc import domain_in_url, replace_domain, extract_urls, remove_query_params
domain_in_url(url, "twitter.com")   # handles subdomains correctly
replace_domain(url, "twitter.com", "fxtwitter.com")
```

### Adding a New Domain/Fix

1. Add entry to `DomainId` enum in [`embed_fixer/fixes.py`](embed_fixer/fixes.py)
2. Add `Domain` with `Website` patterns and `FixMethod` list to `DOMAINS`
3. `FixMethod.id` values must be globally unique integers across all domains
4. `Website.skip_method_ids` can exclude specific fix methods for certain URL patterns

### Error Handling

Use `capture_exception(e)` from [`embed_fixer/utils/misc.py`](embed_fixer/utils/misc.py) (not `sentry_sdk.capture_exception` directly) — it falls back to `logger.exception` when Sentry is not configured.

### Translations

All user-facing strings must use `translator.translate(key, lang=guild_lang)`. Keys are defined in [`l10n/en_US.yaml`](l10n/en_US.yaml). Get guild lang via `await translator.get_guild_lang(guild)`.

### Webhook Username Sanitization

Webhook usernames must use `sanitize_username()` to replace "discord" with "discorɗ" (Discord rejects usernames containing "discord"). The suffix `" (Embed Fixer)"` is appended and used to identify bot-sent webhook messages.

### Database Migrations

- SQLite: manual migration only
- PostgreSQL: `aerich upgrade` (migrations in `/migrations/embed_fixer/`)
- `GuildSettingsOld` in [`embed_fixer/models.py`](embed_fixer/models.py) is the legacy schema — do NOT add new fields there; add to `GuildSettings` (Pydantic model) only

## Code Style

- `from __future__ import annotations` at top of every file
- `TYPE_CHECKING` guard for import-only types
- `type Alias = ...` syntax (Python 3.12 style) for type aliases
- Google docstring convention (enforced by ruff)
- `ruff.toml`: line-length 100, `future-annotations=true`, `skip-magic-trailing-comma=true`
- Pydantic base classes are runtime-evaluated (configured in `ruff.toml` `[lint.flake8-type-checking]`)
