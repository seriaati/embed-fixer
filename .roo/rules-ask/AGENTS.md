# Project Documentation Rules (Non-Obvious Only)

- `GuildSettings` in [`embed_fixer/models.py`](embed_fixer/models.py) is a **Pydantic model**, not a Tortoise ORM model — it wraps `GuildSettingsTable` which stores JSON blobs; this is counterintuitive given the file is named `models.py`
- `GuildSettingsOld` is a frozen legacy Tortoise model kept only for one-time migration on startup — it maps to table `guild_settings` while the active table is `guild_settings_v2`
- Fix methods in [`embed_fixer/fixes.py`](embed_fixer/fixes.py) are pure data (dataclasses), not code — actual URL transformation logic lives in [`embed_fixer/cogs/fixer.py`](embed_fixer/cogs/fixer.py) `_find_fixes()`
- `Website.skip_method_ids` is a per-URL-pattern exclusion list — some fix methods don't work for certain URL shapes within the same domain (e.g. Instagram share links skip InstaFix)
- Translation keys are in [`l10n/en_US.yaml`](l10n/en_US.yaml) — the YAML `name` field in each locale file is the display name, not a key
- `embed_fixer/emojis/` contains PNG files that are auto-uploaded as Discord application emojis on bot startup — filenames become emoji names
- `MockMessage` in [`embed_fixer/cogs/fixer.py`](embed_fixer/cogs/fixer.py) is a duck-typed stand-in for `discord.Message` used only for the `/fix` slash command path
