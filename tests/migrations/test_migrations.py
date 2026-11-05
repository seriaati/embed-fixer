from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import Mock

import pytest
import pytest_asyncio
from aiohttp import ClientSession
from tortoise import Tortoise
from tortoise.context import TortoiseContext
from tortoise.exceptions import IntegrityError
from tortoise.migrations.api.migrate import migrate

from embed_fixer import bot as bot_module
from embed_fixer.bot import EmbedFixer
from embed_fixer.fixes import DomainId
from embed_fixer.models import (
    FixedMessage,
    GuildFixMethod,
    GuildSettings,
    GuildSettingsOld,
    GuildSettingsTable,
    IgnoreMe,
    SponsoredGuild,
    UserSettings,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from pathlib import Path


@pytest_asyncio.fixture
async def migration_db(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[dict[str, Any]]:
    config = {
        "connections": {"default": f"sqlite://{tmp_path / 'migrations.sqlite3'}"},
        "apps": {
            "embed_fixer": {
                "models": ["embed_fixer.models"],
                "default_connection": "default",
                "migrations": "migrations",
            }
        },
    }
    monkeypatch.setattr(bot_module, "TORTOISE_ORM", config)
    async with TortoiseContext() as context:
        await context.init(config=config)
        yield config


@pytest.fixture
def migration_bot() -> EmbedFixer:
    return EmbedFixer(session=Mock(spec=ClientSession), env="dev")


@pytest.mark.usefixtures("migration_db")
async def test_fresh_sqlite_migrations_build_working_schema_and_are_repeatable(
    migration_bot: EmbedFixer,
) -> None:
    assert not await migration_bot._is_pre_migration_db()
    await migration_bot._apply_migrations()
    assert not await migration_bot._is_pre_migration_db()
    guild = await GuildSettings.create(1)
    await UserSettings.create(1)
    await IgnoreMe.add(1)
    await FixedMessage.create(id=1, guild_id=1, channel_id=2, author_id=3, send_type="reply")
    await SponsoredGuild.create(id=1, sponsor_id=3)
    await GuildFixMethod.create(guild_id=guild.id, domain_id=DomainId.TWITTER, fix_id=1)
    with pytest.raises(IntegrityError):
        await GuildFixMethod.create(guild_id=guild.id, domain_id=DomainId.TWITTER, fix_id=1)
    await migration_bot._apply_migrations()
    assert (await GuildSettings.get_or_none(1)) == guild
    assert (await FixedMessage.get(id=1)).author_id == 3
    history = await Tortoise.get_connection("default").execute_query_dict(
        "SELECT app, name FROM tortoise_migrations ORDER BY name"
    )
    assert history == [
        {"app": "embed_fixer", "name": "0001_initial"},
        {"app": "embed_fixer", "name": "0002_auto_20260708_1857"},
        {"app": "embed_fixer", "name": "0003_auto_20261021_0739"},
    ]


@pytest.mark.parametrize("history_table_exists", [False, True])
async def test_pre_migration_database_is_baselined_without_losing_settings(
    *, history_table_exists: bool, migration_bot: EmbedFixer, migration_db: dict[str, Any]
) -> None:
    await migrate(config=migration_db, target="embed_fixer.0001_initial", direction="forward")
    settings = await GuildSettings.create(123)
    settings.lang = "ja"
    settings.disabled_domains = [DomainId.TWITTER]
    await settings.save()
    await GuildSettingsOld.create(id=456, lang="fr")
    conn = Tortoise.get_connection("default")
    if history_table_exists:
        await conn.execute_query("DELETE FROM tortoise_migrations")
    else:
        await conn.execute_query("DROP TABLE tortoise_migrations")
    assert await migration_bot._is_pre_migration_db()
    await migration_bot._apply_migrations()
    loaded = await GuildSettings.get_or_none(123)
    assert loaded == settings
    assert await GuildSettingsOld.get(id=456)
    assert not await migration_bot._is_pre_migration_db()
    await FixedMessage.create(id=5, guild_id=123, channel_id=2, author_id=3, send_type="webhook")
    await SponsoredGuild.create(id=123, sponsor_id=3)
    history = await Tortoise.get_connection("default").execute_query_dict(
        "SELECT name FROM tortoise_migrations ORDER BY name"
    )
    assert len(history) == 3


@pytest.mark.usefixtures("migration_db")
async def test_legacy_only_table_is_detected_and_missing_tables_are_tolerated(
    migration_bot: EmbedFixer,
) -> None:
    conn = Tortoise.get_connection("default")
    await conn.execute_script("CREATE TABLE guild_settings (id BIGINT PRIMARY KEY)")
    assert await migration_bot._is_pre_migration_db()


@pytest.mark.usefixtures("db")
async def test_legacy_guild_settings_copy_preserves_all_fields_and_existing_new_rows(
    migration_bot: EmbedFixer,
) -> None:
    values: dict[str, Any] = {
        "disable_webhook_reply": True,
        "disabled_fixes": ["twitter"],
        "disabled_domains": [1, 2],
        "disable_fix_channels": [3],
        "enable_fix_channels": [4],
        "extract_media_channels": [5],
        "disable_image_spoilers": [6],
        "show_post_content_channels": [7],
        "disable_delete_reaction": True,
        "lang": "ja",
        "use_vxreddit": True,
        "delete_msg_emoji": "🗑️",
        "bot_visibility": True,
        "funnel_target_channel": 8,
        "whitelist_role_ids": [9],
        "translate_target_lang": "fr",
        "show_original_link_btn": True,
    }
    await GuildSettingsOld.create(id=1, **values)
    await GuildSettingsOld.create(id=2, lang="fr")
    existing = await GuildSettings.create(2)
    existing.lang = "en_US"
    existing.disabled_domains = [3]
    await existing.save()
    await migration_bot._migrate_guild_settings()
    migrated = await GuildSettings.get_or_none(1)
    assert migrated is not None
    assert {name: getattr(migrated, name) for name in values} == values
    assert (await GuildSettings.get_or_none(2)) == existing
    await migration_bot._migrate_guild_settings()
    assert await GuildSettingsTable.all().count() == 2
    assert await GuildSettingsOld.all().count() == 2
