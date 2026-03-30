# Project Debug Rules (Non-Obvious Only)

- Logs go to `logs/` directory (configured via loguru in [`embed_fixer/utils/logging.py`](embed_fixer/utils/logging.py))
- `capture_exception(e)` in [`embed_fixer/utils/misc.py`](embed_fixer/utils/misc.py) silently swallows exceptions to Sentry when `SENTRY_DSN` is set — if Sentry is not configured it falls back to `logger.exception`
- Health cog ([`embed_fixer/cogs/health.py`](embed_fixer/cogs/health.py)) is skipped entirely in `ENV=dev` — only loaded in `prod`
- Bot-sent webhook messages are identified by `" (Embed Fixer)"` suffix in `display_name` — messages without this suffix are NOT bot-sent even if `webhook_id` is set
- `GuildSettingsOld` (legacy Tortoise model, table `guild_settings`) and `GuildSettingsTable` (new, table `guild_settings_v2`) coexist — queries against the wrong table will silently return empty results
- `aiohttp-cache.sqlite` is the HTTP cache file created at runtime by `aiohttp-client-cache` — not a database
- `asyncio.create_task()` calls in [`embed_fixer/cogs/fixer.py`](embed_fixer/cogs/fixer.py) are fire-and-forget; failures there won't propagate to the caller
- Discord HTTP error code 50035 (Invalid Form Body) is intentionally ignored in several places — it usually means "Unknown message" and is a race condition, not a bug
