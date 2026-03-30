# Project Coding Rules (Non-Obvious Only)

- Every `.py` file must start with `from __future__ import annotations`
- Import-only types go under `if TYPE_CHECKING:` guard to avoid runtime cost
- Use `type Alias = ...` (Python 3.12 syntax), not `TypeAlias = ...`
- Pydantic models (`BaseModel`, `BaseSettings`) are runtime-evaluated — do NOT move their imports under `TYPE_CHECKING` (configured in `ruff.toml` `[lint.flake8-type-checking]`)
- `GuildSettings`/`UserSettings` are Pydantic models stored as JSON in Tortoise — never use `.filter()` or `.get()` on them directly; always use `.get_or_create()`, `.get_or_none()`, `.save()`
- New settings fields go in `GuildSettings` (Pydantic) only — `GuildSettingsOld` is frozen legacy for migration
- `FixMethod.id` must be a globally unique integer across ALL domains in [`embed_fixer/fixes.py`](embed_fixer/fixes.py)
- Use `capture_exception(e)` from [`embed_fixer/utils/misc.py`](embed_fixer/utils/misc.py), never `sentry_sdk.capture_exception` directly
- Webhook usernames must call `sanitize_username()` — Discord API rejects names containing "discord"
- Bot-sent webhook messages are identified by the `" (Embed Fixer)"` suffix in `display_name`
- All user-facing strings require `translator.translate(key, lang=guild_lang)` — no hardcoded English strings
- URL manipulation must use helpers in [`embed_fixer/utils/misc.py`](embed_fixer/utils/misc.py): `domain_in_url`, `replace_domain`, `extract_urls`, `remove_query_params` — never `str.find()` or naive string replacement on URLs
- `ruff.toml` enforces `skip-magic-trailing-comma=true` — don't add trailing commas to force multi-line
