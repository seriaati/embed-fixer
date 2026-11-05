from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from embed_fixer.cogs import settings
from embed_fixer.fixes import DomainId
from embed_fixer.models import GuildFixMethod, GuildSettings, IgnoreMe, UserSettings
from embed_fixer.settings import GuildSetting
from embed_fixer.ui.guild_settings import (
    DeleteMsgEmojiModal,
    GuildSettingsView,
    RemoveReactionsAfterModal,
)
from embed_fixer.ui.reset_settings import ResetSettingsView
from embed_fixer.ui.user_settings import UserSettingsView
from tests.support.cogs import bot
from tests.support.ui import interaction

if TYPE_CHECKING:
    from typing import Any


@pytest.mark.usefixtures("db")
async def test_settings_migration_maps_legacy_domains_deduplicates_and_upserts_reddit() -> None:
    await settings.SettingsCog._db_migration(100)
    current = await GuildSettings.create(100)
    current.disabled_fixes = ["x.com", "twitter.com", "unknown", "reddit.com"]
    current.disabled_domains = [DomainId.TWITTER.value]
    current.use_vxreddit = True
    await current.save()
    for _ in range(2):
        await settings.SettingsCog._db_migration(100)
    stored = (await GuildSettings.get_or_create(100))[0]
    assert set(stored.disabled_domains) == {DomainId.TWITTER.value, DomainId.REDDIT.value}
    assert stored.disabled_fixes == []
    assert not stored.use_vxreddit
    assert (
        await GuildFixMethod.filter(guild_id=100, domain_id=DomainId.REDDIT, fix_id=7).count() == 1
    )
    stored.use_vxreddit = True
    await stored.save()
    await settings.SettingsCog._db_migration(100)
    assert await GuildFixMethod.filter(guild_id=100).count() == 1


@pytest.mark.usefixtures("db")
@pytest.mark.parametrize("setting", list(GuildSetting))
async def test_settings_command_routes_every_setting(setting: GuildSetting) -> None:
    cog: Any = settings.SettingsCog(bot())
    i = interaction()
    await cog.settings.callback(cog, i, setting)
    if setting in {GuildSetting.DELETE_MSG_EMOJI, GuildSetting.REMOVE_REACTIONS_AFTER}:
        modal = i.response.send_modal.await_args.args[0]
        assert isinstance(
            modal,
            DeleteMsgEmojiModal
            if setting == GuildSetting.DELETE_MSG_EMOJI
            else RemoveReactionsAfterModal,
        )
    else:
        assert isinstance(i.followup.send.await_args.kwargs["view"], GuildSettingsView)


@pytest.mark.usefixtures("db")
@pytest.mark.parametrize(
    "command_name",
    [
        "settings",
        "translang_command",
        "reset_settings_command",
        "export_settings_command",
        "import_settings_command",
    ],
)
async def test_guild_commands_guard_dm_and_have_permission_metadata(command_name: str) -> None:
    cog: Any = settings.SettingsCog(bot())
    command = getattr(cog, command_name)
    i = interaction(guild_id=None)
    extra = {
        "settings": (GuildSetting.LANG,),
        "translang_command": ("en",),
        "import_settings_command": (MagicMock(),),
    }.get(command_name, ())
    await command.callback(cog, i, *extra)
    i.response.defer.assert_not_awaited()
    i.response.send_message.assert_not_awaited()
    assert command.default_permissions.value == 0
    assert command.allowed_contexts.guild
    assert not command.allowed_contexts.dm_channel
    assert not command.allowed_installs.user


@pytest.mark.usefixtures("db")
@pytest.mark.parametrize("language", ["en", "ja", "DISABLE", "invalid"])
async def test_translate_command_validates_and_persists_target(language: str) -> None:
    cog: Any = settings.SettingsCog(bot())
    initial = await GuildSettings.create(100)
    initial.translate_target_lang = "fr"
    await initial.save()
    i = interaction()
    await cog.translang_command.callback(cog, i, language)
    stored = (await GuildSettings.get_or_create(100))[0]
    if language == "invalid":
        assert stored.translate_target_lang == "fr"
        i.response.send_message.assert_awaited_once()
        i.response.defer.assert_not_awaited()
    else:
        assert stored.translate_target_lang == (None if language == "DISABLE" else language)
        i.response.defer.assert_awaited_once_with(ephemeral=True)
        assert i.followup.send.await_args.kwargs["ephemeral"]


async def test_translation_autocomplete_matches_case_insensitive_names_and_codes_and_caps() -> None:
    cog: Any = settings.SettingsCog(bot())
    all_choices = await cog.translang_autocomplete(interaction(), "")
    assert len(all_choices) == 25
    assert all_choices[0].value == "disable"
    english = await cog.translang_autocomplete(interaction(), "ENGLISH")
    assert "en" in {choice.value for choice in english}
    disabled = await cog.translang_autocomplete(interaction(), "DiSaBlE")
    assert [choice.value for choice in disabled] == ["disable"]
    assert await cog.translang_autocomplete(interaction(), "zzzzzz") == []


@pytest.mark.usefixtures("db")
async def test_reset_command_starts_confirmation_and_owner_debug_prints_settings() -> None:
    cog: Any = settings.SettingsCog(bot())
    i = interaction()
    await cog.reset_settings_command.callback(cog, i)
    assert isinstance(i.response.send_message.await_args.kwargs["view"], ResetSettingsView)
    ctx = interaction()
    ctx.send = AsyncMock()
    await cog.get_guild_settings.callback(cog, ctx)
    assert ctx.send.await_args is not None
    assert "id=100" in ctx.send.await_args.args[0]
    ctx.guild = None
    ctx.send.reset_mock()
    await cog.get_guild_settings.callback(cog, ctx)
    ctx.send.assert_not_awaited()


@pytest.mark.usefixtures("db")
async def test_export_and_import_round_trip_real_json_and_fix_methods() -> None:
    cog: Any = settings.SettingsCog(bot())
    source = await GuildSettings.create(100)
    source.disabled_domains = [DomainId.INSTAGRAM.value]
    source.lang = "en_US"
    source.funnel_target_channel = 12345
    source.hide_webhook_suffix = True
    await source.save()
    await GuildFixMethod.create(guild_id=100, domain_id=DomainId.REDDIT, fix_id=7)
    i = interaction()
    await cog.export_settings_command.callback(cog, i)
    file = i.followup.send.await_args.kwargs["file"]
    assert isinstance(file, discord.File)
    assert file.filename == "embed_fixer_settings_100.json"
    payload = file.fp.read()
    data = json.loads(payload)
    assert "id" not in data["guild_settings"]
    assert data["fix_methods"] == [{"domain_id": DomainId.REDDIT.value, "fix_id": 7}]
    data["fix_methods"] *= 2
    await GuildSettings.create(101)
    await GuildFixMethod.create(guild_id=101, domain_id=DomainId.TWITTER, fix_id=1)
    attachment = MagicMock(
        size=len(payload), read=AsyncMock(return_value=json.dumps(data).encode())
    )
    imported = interaction(guild_id=101)
    await cog.import_settings_command.callback(cog, imported, attachment)
    stored = (await GuildSettings.get_or_create(101))[0]
    assert stored.model_dump(exclude={"id"}) == source.model_dump(exclude={"id"})
    assert await GuildFixMethod.filter(guild_id=101).count() == 1
    assert (await GuildFixMethod.get(guild_id=101)).domain_id == DomainId.REDDIT
    assert "import" in imported.followup.send.await_args.args[0].lower()


@pytest.mark.usefixtures("db")
@pytest.mark.parametrize(
    "payload",
    [
        b"invalid",
        b"{}",
        b"null",
        b"[]",
        b'{"guild_settings":null}',
        b'{"guild_settings":{"disabled_domains":"bad"}}',
        b'{"guild_settings":{},"fix_methods":[{}]}',
        b'{"guild_settings":{},"fix_methods":[{"domain_id":99999,"fix_id":1}]}',
        b'{"guild_settings":{},"fix_methods":[{"domain_id":1,"fix_id":"x"}]}',
    ],
)
async def test_import_rejects_invalid_payloads_without_mutation(payload: bytes) -> None:
    original = await GuildSettings.create(100)
    original.bot_visibility = True
    await original.save()
    await GuildFixMethod.create(guild_id=100, domain_id=DomainId.TWITTER, fix_id=1)
    cog: Any = settings.SettingsCog(bot())
    attachment = MagicMock(size=len(payload), read=AsyncMock(return_value=payload))
    i = interaction()
    await cog.import_settings_command.callback(cog, i, attachment)
    assert (await GuildSettings.get_or_create(100))[0].bot_visibility
    assert await GuildFixMethod.filter(guild_id=100).count() == 1
    assert i.followup.send.await_args.kwargs["ephemeral"]


@pytest.mark.usefixtures("db")
async def test_import_rejects_oversized_attachment_without_reading_and_accepts_empty_fixes() -> (
    None
):
    cog: Any = settings.SettingsCog(bot())
    attachment = MagicMock(size=1024 * 1024 + 1, read=AsyncMock())
    i = interaction()
    await cog.import_settings_command.callback(cog, i, attachment)
    attachment.read.assert_not_awaited()
    attachment.size = 1024 * 1024
    attachment.read.return_value = b'{"guild_settings":{"bot_visibility":true}}'
    await cog.import_settings_command.callback(cog, i, attachment)
    assert (await GuildSettings.get_or_create(100))[0].bot_visibility
    assert await GuildFixMethod.filter(guild_id=100).count() == 0


@pytest.mark.usefixtures("db")
async def test_ignore_me_toggles_and_user_settings_opens_in_dm() -> None:
    cog: Any = settings.SettingsCog(bot())
    i = interaction(guild_id=None)
    for expected in (True, False):
        await cog.ignore_me_command.callback(cog, i)
        assert await IgnoreMe.contains(200) is expected
        assert i.followup.send.await_args.kwargs["ephemeral"]
    await cog.user_settings_command.callback(cog, i)
    assert isinstance(i.followup.send.await_args.kwargs["view"], UserSettingsView)
    assert await UserSettings.get_or_none(200) is not None
    for command in (cog.ignore_me_command, cog.user_settings_command):
        assert command.allowed_contexts.dm_channel
        assert command.allowed_installs.user


@pytest.mark.parametrize("module", [settings])
async def test_cog_setup_registers_expected_cog(module: Any) -> None:
    client = bot()
    await module.setup(client)
    assert client.add_cog.await_count == 1
    assert client.add_cog.await_args.args[0].bot is client
