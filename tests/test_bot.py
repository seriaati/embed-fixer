from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, Mock, call

import discord
import pytest
from aiohttp import ClientResponse, ClientSession
from discord.ext import commands
from tortoise.exceptions import IntegrityError

from embed_fixer import bot as bot_module
from embed_fixer.bot import EmbedFixer
from embed_fixer.core.command_tree import CommandTree
from embed_fixer.core.translator import AppCommandTranslator
from embed_fixer.models import GuildSettings

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def bot() -> EmbedFixer:
    return EmbedFixer(session=Mock(spec=ClientSession), env="dev")


def test_bot_configuration_supports_fixing_and_user_installs(bot: EmbedFixer) -> None:
    assert bot.env == "dev"
    assert isinstance(bot.tree, CommandTree)
    assert bot.intents.guilds
    assert bot.intents.message_content
    assert bot.intents.reactions
    assert bot.allowed_mentions is not None
    assert bot.allowed_mentions.everyone is False
    assert bot.help_command is None
    assert bot.app_emojis == {}
    assert bot_module.permissions.manage_webhooks
    assert bot_module.permissions.manage_messages
    assert bot_module.allowed_installs.guild
    assert bot_module.allowed_installs.user
    assert bot_module.allowed_contexts.guild
    assert bot_module.allowed_contexts.dm_channel
    assert bot_module.allowed_contexts.private_channel


@pytest.mark.parametrize("env", ["dev", "prod"])
async def test_setup_initializes_database_before_cogs_and_finishes_after_cog_failure(
    env: str, bot: EmbedFixer, monkeypatch: pytest.MonkeyPatch
) -> None:
    bot.env = env
    bot._connection.user = Mock(spec=discord.ClientUser, id=123)
    steps: list[str] = []

    def step(name: str) -> AsyncMock:
        def run(*_args: Any, **_kwargs: Any) -> None:
            steps.append(name)

        return AsyncMock(side_effect=run)

    def load_extension(name: str) -> None:
        steps.append(name)
        if name == "embed_fixer.cogs.admin":
            message = "broken extension"
            raise commands.ExtensionFailed(name, RuntimeError(message))

    monkeypatch.setattr(bot_module.Tortoise, "init", step("db_init"))
    monkeypatch.setattr(bot, "_apply_migrations", step("migrations"))
    monkeypatch.setattr(bot_module.Tortoise, "generate_schemas", step("schemas"))
    monkeypatch.setattr(bot, "_migrate_guild_settings", step("legacy_settings"))
    monkeypatch.setattr(bot, "load_extension", AsyncMock(side_effect=load_extension))
    monkeypatch.setattr(bot_module.translator, "load", step("translations"))
    set_translator = step("command_translator")
    monkeypatch.setattr(bot.tree, "set_translator", set_translator)
    monkeypatch.setattr(bot, "_create_app_emojis", step("emoji_create"))
    monkeypatch.setattr(bot, "_load_app_emojis", step("emoji_load"))
    await bot.setup_hook()
    assert steps[:4] == ["db_init", "migrations", "schemas", "legacy_settings"]
    assert "embed_fixer.cogs.fixer" in steps
    assert "embed_fixer.cogs.admin" in steps
    assert ("embed_fixer.cogs.health" in steps) is (env == "prod")
    assert steps[-5:] == [
        "jishaku",
        "translations",
        "command_translator",
        "emoji_create",
        "emoji_load",
    ]
    assert isinstance(set_translator.call_args.args[0], AppCommandTranslator)


async def test_setup_propagates_database_errors_before_loading_cogs(
    bot: EmbedFixer, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        bot_module.Tortoise, "init", AsyncMock(side_effect=RuntimeError("database unavailable"))
    )
    load = AsyncMock()
    monkeypatch.setattr(bot, "load_extension", load)
    with pytest.raises(RuntimeError, match="database unavailable"):
        await bot.setup_hook()
    load.assert_not_awaited()


async def test_create_app_emojis_skips_existing_and_continues_after_http_error(
    bot: EmbedFixer, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    emoji_dir = tmp_path / "embed_fixer" / "emojis"
    emoji_dir.mkdir(parents=True)
    (emoji_dir / "EXISTING.png").write_bytes(b"existing")
    (emoji_dir / "NEW.png").write_bytes(b"new")
    (emoji_dir / "BROKEN.png").write_bytes(b"broken")
    monkeypatch.chdir(tmp_path)
    existing = Mock(spec=discord.Emoji)
    existing.name = "EXISTING"
    monkeypatch.setattr(bot, "fetch_application_emojis", AsyncMock(return_value=[existing]))

    def create(*, name: str, image: bytes) -> None:
        if name == "BROKEN":
            response = Mock(spec=ClientResponse, status=500, reason="Error")
            raise discord.HTTPException(response, "upload failed")
        assert name == "NEW"
        assert image == b"new"

    create_mock = AsyncMock(side_effect=create)
    monkeypatch.setattr(bot, "create_application_emoji", create_mock)
    await bot._create_app_emojis()
    assert {entry.kwargs["name"] for entry in create_mock.await_args_list} == {"NEW", "BROKEN"}


async def test_load_app_emojis_replaces_stale_cache(
    bot: EmbedFixer, monkeypatch: pytest.MonkeyPatch
) -> None:
    emoji = Mock(spec=discord.Emoji, id=1)
    emoji.name = "NEW"
    old_emoji = Mock(spec=discord.Emoji)
    old_emoji.name = "OLD"
    bot.app_emojis = {"OLD": old_emoji}
    monkeypatch.setattr(bot, "fetch_application_emojis", AsyncMock(return_value=[emoji]))
    await bot._load_app_emojis()
    assert bot.app_emojis == {"NEW": emoji}


@pytest.mark.usefixtures("db")
async def test_guild_join_persists_defaults(bot: EmbedFixer) -> None:
    guild = Mock(spec=discord.Guild, id=123)
    guild.name = "Example"
    await bot.on_guild_join(guild)
    assert await GuildSettings.get_or_none(123) == GuildSettings(id=123)


async def test_guild_join_handles_duplicate_race(
    bot: EmbedFixer, monkeypatch: pytest.MonkeyPatch
) -> None:
    guild = Mock(spec=discord.Guild, id=123)
    guild.name = "Example"
    monkeypatch.setattr(GuildSettings, "create", AsyncMock(side_effect=IntegrityError("duplicate")))
    await bot.on_guild_join(guild)


async def test_command_errors_ignore_check_failures_and_delegate_others(
    bot: EmbedFixer, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent_error = AsyncMock()
    monkeypatch.setattr(commands.AutoShardedBot, "on_command_error", parent_error)
    context = Mock(spec=commands.Context)
    await bot.on_command_error(context, commands.CheckFailure())
    parent_error.assert_not_awaited()
    error = commands.CommandNotFound("missing")
    await bot.on_command_error(context, error)
    parent_error.assert_awaited_once_with(context, error)


async def test_close_disconnects_database_before_discord(
    bot: EmbedFixer, monkeypatch: pytest.MonkeyPatch
) -> None:
    tracker = Mock()
    disconnect_db = AsyncMock()
    disconnect_discord = AsyncMock()
    tracker.attach_mock(disconnect_db, "database")
    tracker.attach_mock(disconnect_discord, "discord")
    monkeypatch.setattr(bot_module.Tortoise, "close_connections", disconnect_db)
    monkeypatch.setattr(commands.AutoShardedBot, "close", disconnect_discord)
    await bot.close()
    assert tracker.mock_calls == [call.database(), call.discord()]


@pytest.mark.parametrize("event", ["apply_start", "apply_success"])
def test_migration_progress_logs_only_start_events(
    event: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    logger = Mock()
    monkeypatch.setattr(bot_module, "logger", logger)
    EmbedFixer._report_migration(event, "embed_fixer", "0001_initial")
    if event == "apply_start":
        logger.info.assert_called_once_with("Applying migration embed_fixer.0001_initial")
    else:
        logger.info.assert_not_called()
