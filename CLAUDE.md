# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv run run.py       # Start the bot
ruff check --fix .  # Lint with auto-fix
ruff format .       # Format
pyright             # Type check
```

No automated test suite — test manually in a Discord server. There is no way to run a single test.

## Environment Variables (`.env`)

- `DISCORD_TOKEN` — required
- `DB_URI` — defaults to `sqlite://embed_fixer.db` (PostgreSQL supported via `asyncpg` optional dep)
- `ENV` — `dev` or `prod` (health cog skipped in `dev`)
- `REDIS_URL`, `SENTRY_DSN`, `PROXY_URL`, `HEARTBEAT_URL` — optional

## Architecture

A Python 3.12 Discord bot (`discord.py` `AutoShardedBot`) with Tortoise ORM, Pydantic v2, `loguru`, and Sentry.

**`embed_fixer/`**

- `bot.py` — `EmbedFixer` bot class, sets up intents, cogs, and startup
- `fixes.py` — Domain/fix registry: `DomainId` enum, `Domain`/`Website`/`FixMethod` data classes, and the `DOMAINS` constant that maps every supported platform to its fix methods
- `settings.py` — `GuildSetting` and `UserSetting` enums
- `models.py` — Tortoise ORM table models (`SettingsTable`, `GuildSettingsOld` legacy schema); `GuildSettings`/`UserSettings` Pydantic wrappers live here too
- `health.py` — heartbeat health-check endpoint (skipped in `dev` mode)

**`embed_fixer/cogs/`** — discord.py Cog extensions

- `fixer.py` — core embed-fixing logic: listens to messages, finds matching domains, applies fixes via webhook/reply, handles media extraction, delete-reaction flow
- `settings.py` — `/settings` slash commands
- `admin.py`, `info.py`, `health.py` — admin/info/health-check cogs

**`embed_fixer/core/`**

- `translator.py` — loads YAML locale files from `l10n/`, resolves guild language, provides `translator.translate(key, lang=...)`
- `config.py` — `pydantic-settings` app config (reads env vars)
- `db_config.py` — Tortoise ORM init config
- `command_tree.py` — custom `CommandTree` for slash command error handling

**`embed_fixer/ui/`** — discord.py Views/Selects for settings menus

**`embed_fixer/utils/`**

- `misc.py` — URL helpers (`domain_in_url`, `replace_domain`, `extract_urls`, `remove_query_params`), `capture_exception`, `sanitize_username`
- `fetch_info.py` — fetches post metadata from social platforms
- `download_media.py` — downloads media files for extraction
- `embed.py` — embed-building helpers

**`l10n/`** — YAML translation files; `en_US.yaml` is the source of truth for all translation keys

**`migrations/embed_fixer/`** — Aerich migration files (PostgreSQL only; SQLite requires manual migration)

## Critical Patterns

### Settings (non-obvious architecture)

`GuildSettings` and `UserSettings` are **Pydantic models**, NOT Tortoise ORM models. They are stored as JSON blobs in `SettingsTable`. Always use the Pydantic class methods:

```python
settings, created = await GuildSettings.get_or_create(guild_id)
settings = await GuildSettings.get_or_none(guild_id)
await settings.save()
```

Never query `GuildSettingsTable` directly — use the Pydantic wrapper.

### URL Helpers

Use helpers from `embed_fixer/utils/misc.py` instead of raw string methods:

```python
from embed_fixer.utils.misc import domain_in_url, replace_domain, extract_urls, remove_query_params
domain_in_url(url, "twitter.com")  # handles subdomains correctly
replace_domain(url, "twitter.com", "fxtwitter.com")
```

### Adding a New Domain/Fix

1. Add entry to `DomainId` enum in `embed_fixer/fixes.py`
2. Add `Domain` with `Website` patterns and `FixMethod` list to `DOMAINS`
3. `FixMethod.id` values must be globally unique integers across all domains
4. `Website.skip_method_ids` can exclude specific fix methods for certain URL patterns

### Error Handling

Use `capture_exception(e)` from `embed_fixer/utils/misc.py` — not `sentry_sdk.capture_exception` directly. It falls back to `logger.exception` when Sentry is not configured.

### Translations

All user-facing strings must use `translator.translate(key, lang=guild_lang)`. Keys are defined in `l10n/en_US.yaml`. Get guild lang via `await translator.get_guild_lang(guild)`.

### Webhook Username Sanitization

Webhook usernames must use `sanitize_username()` to replace "discord" with "discorɗ" (Discord rejects usernames containing "discord"). The suffix `" (Embed Fixer)"` is appended to identify bot-sent webhook messages.

### Database Migrations

- SQLite: manual migration only
- PostgreSQL: `aerich upgrade`
- `GuildSettingsOld` in `embed_fixer/models.py` is the legacy schema — do NOT add new fields there; add to `GuildSettings` (Pydantic model) only

## Code Style

- `from __future__ import annotations` at the top of every file
- `TYPE_CHECKING` guard for import-only types
- `type Alias = ...` syntax (Python 3.12) for type aliases
- Google docstring convention (enforced by ruff)
- Line length 100, `skip-magic-trailing-comma = true`
- Pydantic base classes are runtime-evaluated (configured in `ruff.toml` under `[lint.flake8-type-checking]`)
