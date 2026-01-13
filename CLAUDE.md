# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Embed Fixer is a Discord bot that fixes social media embeds by replacing URLs with embed-friendly services (fxtwitter, phixiv, etc.). It intercepts messages, detects social media URLs, deletes the original message, and resends it via webhook with fixed URLs.

## Development Commands

### Running the Bot

```bash
# Start the bot
uv run run.py

# With environment variables in .env file
# Required: DISCORD_TOKEN
# Optional: DB_URI (defaults to sqlite:///data/embed_fixer.db), ENV (dev/prod), REDIS_URL
```

### Linting and Formatting

```bash
# Run ruff linter
uv run ruff check .

# Run ruff formatter
uv run ruff format .

# Both are configured via ruff.toml (line-length: 100, target: py312)
# Pre-commit hooks auto-run these on commit
```

### Type Checking

```bash
# Run pyright type checker
uv run pyright

# Configured in pyproject.toml with standard type checking mode
```

### Database Migrations

```bash
# Apply migrations (PostgreSQL only, SQLite requires manual migration)
aerich upgrade

# Migrations are in /migrations/embed_fixer
# Database config is in embed_fixer/core/db_config.py
```

### Command Syncing

```bash
# Sync slash commands with Discord
# Use bot mention as prefix: @EmbedFixer sync
# Requires bot restart and Discord client restart to see changes
```

## Architecture

### Core Components

- **[embed_fixer/bot.py](embed_fixer/bot.py)**: Main `EmbedFixer` bot class (AutoShardedBot)
  - Handles bot initialization, cog loading, and database setup
  - Entry point sets up intents, permissions, and translator
  - Auto-migrates old guild settings on startup

- **[embed_fixer/fixes.py](embed_fixer/fixes.py)**: Fix service definitions
  - `DOMAINS` list contains all supported platforms (Twitter, Pixiv, TikTok, etc.)
  - Each `Domain` has multiple `FixMethod` options (FxEmbed, BetterTwitFix, etc.)
  - URL pattern matching via regex `Website` objects
  - Fix methods define domain replacements (e.g., twitter.com → fxtwitter.com)

- **[embed_fixer/models.py](embed_fixer/models.py)**: Database models
  - `GuildSettings`: Per-guild configuration (Pydantic model stored as JSON in Tortoise ORM)
  - `IgnoreMe`: User opt-out list
  - `GuildFixMethod`: Per-guild fix method preferences
  - Uses Tortoise ORM with JSON storage for flexibility

### Cog Structure

- **[embed_fixer/cogs/fixer.py](embed_fixer/cogs/fixer.py)**: Main embed fixing logic
  - `on_message`: Intercepts messages, detects URLs, performs fixes
  - Context menu commands: "fix_embed", "extract_medias"
  - Webhook creation and message resending
  - Media extraction for supported platforms
  - NSFW detection and filtering

- **[embed_fixer/cogs/settings.py](embed_fixer/cogs/settings.py)**: Guild configuration commands
  - `/settings` command with extensive configuration options
  - Language selection, channel blacklists/whitelists, fix method selection

- **[embed_fixer/cogs/admin.py](embed_fixer/cogs/admin.py)**: Admin commands for bot owner
- **[embed_fixer/cogs/info.py](embed_fixer/cogs/info.py)**: Bot information commands
- **[embed_fixer/cogs/health.py](embed_fixer/cogs/health.py)**: Health check endpoint (production only)

### Utilities

- **[embed_fixer/utils/fetch_info.py](embed_fixer/utils/fetch_info.py)**: API clients for social media platforms
  - Fetches post info (NSFW status, media URLs, content) from Twitter, Pixiv, Kemono, etc.
  - Used for NSFW filtering and media extraction

- **[embed_fixer/utils/download_media.py](embed_fixer/utils/download_media.py)**: Media downloading for extraction feature
- **[embed_fixer/utils/misc.py](embed_fixer/utils/misc.py)**: URL manipulation helpers (domain_in_url, replace_domain, etc.)

### Translation System

- **[embed_fixer/core/translator.py](embed_fixer/core/translator.py)**: i18n support via Transifex
- Loads translations from YAML files
- Used for slash commands and bot responses

## Fix Flow

1. User sends message with social media URL
2. `FixerCog.on_message` detects URL and matches against `DOMAINS`
3. Checks guild settings (disabled domains, channel blacklist/whitelist, user opt-out)
4. For NSFW platforms (Twitter, Pixiv), fetches post info to check NSFW status
5. Applies fix method (URL domain replacement) based on guild preferences
6. Deletes original message
7. Creates/reuses webhook with user's name and avatar
8. Sends fixed message via webhook
9. Adds delete reaction emoji (❌) for original author to delete

## Media Extraction Flow

1. Enabled for specific channels via `/settings`
2. Detects URLs from supported platforms (Twitter, Pixiv, Iwara, Kemono, Bluesky)
3. Fetches all media URLs from post
4. Downloads media (if within file size limits)
5. Sends as gallery-like layout
6. Auto-spoilers NSFW content (configurable)

## Important Patterns

### Guild Settings

All settings are per-guild and stored in `GuildSettings` model. Access via:

```python
settings, _ = await GuildSettings.get_or_create(guild_id)
```

### Fix Method Selection

Each domain can have multiple fix methods. Guilds can override the default via `GuildFixMethod` table:

```python
guild_fix = await GuildFixMethod.get_or_none(guild_id=guild_id, domain_id=domain.id)
fix_method = domain.get_fix_method(guild_fix.fix_id) if guild_fix else domain.default_fix_method
```

### URL Matching

Use `domain_in_url()` helper instead of `str.find()` to properly handle subdomains and query params:

```python
from embed_fixer.utils.misc import domain_in_url

if domain_in_url("twitter.com", url):
    # Match twitter.com and subdomains (www.twitter.com, mobile.twitter.com, etc.)
```

### Webhook Management

Webhooks are created per-channel and reused. The bot requires `manage_webhooks` permission:

```python
webhook = await channel.create_webhook(name="Embed Fixer")
await webhook.send(content=fixed_content, username=author.display_name, avatar_url=author.display_avatar.url)
```

## Testing

The bot does not have a formal test suite. Test manually in a Discord server:

1. Create a test server
2. Invite the bot
3. Send messages with social media URLs
4. Verify embeds are fixed correctly
5. Test various settings combinations via `/settings`
