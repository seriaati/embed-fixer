# Project Architecture Rules (Non-Obvious Only)

- Settings are a two-layer architecture: `SettingsTable` (Tortoise, stores raw JSON) + `BaseSettings` (Pydantic, typed wrapper) — adding a new setting field requires only a Pydantic field with a default; no DB migration needed for SQLite
- `GuildFixMethod` is a separate Tortoise table (not part of `GuildSettings` JSON) because it needs per-domain querying — it's the only settings-related model that IS a real ORM model
- Fix method selection is lazy: `domain.default_fix_method` returns the first `FixMethod` with `default=True`, falling back to `fix_methods[0]` — order in `DOMAINS` list matters
- `Website.skip_method_ids` creates a many-to-many exclusion between URL patterns and fix methods within a single domain — required when a fix service doesn't support a URL variant (e.g. short-link vs full URL)
- The bot uses `AutoShardedBot` but `chunk_guilds_at_startup=False` and `MemberCacheFlags.none()` — member data is never cached; always fetch on demand
- Webhook identity: the bot creates one webhook per `TextChannel` named after `bot.user.name`; threads reuse the parent channel's webhook (threads don't support webhooks directly)
- `send_type` return value from `_send_message` drives post-send behavior: `"webhook"/"channel"` → delete original; `"reply"` → suppress embed + remove ⌛ reaction; `None` → HTTP error, already handled
- `extract_urls()` returns `(url, is_spoilered)` tuples — spoilered URLs (`||url||`) are tracked separately so media extracted from them is auto-spoilered
- `FixMethod.id=1` is hardcoded in `_find_fixes` to detect FxEmbed for translation appending — this coupling must be preserved if FxEmbed's ID ever changes
