from __future__ import annotations

import re

import pytest
from pydantic import ValidationError
from tortoise.exceptions import IntegrityError

from embed_fixer.fixes import DomainId
from embed_fixer.models import (
    FixedMessage,
    GuildFixMethod,
    GuildSettings,
    GuildSettingsOld,
    GuildSettingsTable,
    IgnoreMe,
    ProxyTag,
    SettingsTable,
    SponsoredGuild,
    UserSettings,
    UserSettingsTable,
)
from embed_fixer.settings import FixMode, GuildSetting, UserSetting


@pytest.mark.parametrize(
    ("settings_class", "table_class"),
    [(GuildSettings, GuildSettingsTable), (UserSettings, UserSettingsTable)],
)
@pytest.mark.usefixtures("db")
async def test_settings_create_update_reload_delete(
    settings_class: type[GuildSettings] | type[UserSettings], table_class: type[SettingsTable]
) -> None:
    assert await settings_class.get_or_none(123) is None
    settings, created = await settings_class.get_or_create(123)
    assert created
    assert settings.id == 123
    settings.lang = "ja_JP"
    await settings.save(update_fields=["lang"])
    loaded, created = await settings_class.get_or_create(123)
    assert not created
    assert loaded.lang == "ja_JP"
    assert loaded is not settings
    nullable_loaded = await settings_class.get_or_none(123)
    assert nullable_loaded is not None
    assert nullable_loaded.lang == "ja_JP"
    row = await table_class.get(id=123)
    assert "id" not in row.data
    assert row.data["lang"] == "ja_JP"
    await settings_class.delete(123)
    await settings_class.delete(123)
    assert await settings_class.get_or_none(123) is None


@pytest.mark.parametrize(
    ("settings_class", "table_class"),
    [(GuildSettings, GuildSettingsTable), (UserSettings, UserSettingsTable)],
)
@pytest.mark.usefixtures("db")
async def test_empty_settings_rows_are_repaired_with_defaults(
    settings_class: type[GuildSettings] | type[UserSettings], table_class: type[SettingsTable]
) -> None:
    await table_class.create(id=1, data={})
    assert await settings_class.get_or_none(1) is None
    settings, created = await settings_class.get_or_create(1)
    assert not created
    assert settings == settings_class(id=1)
    assert (await table_class.get(id=1)).data


@pytest.mark.usefixtures("db")
async def test_guild_and_user_settings_have_independent_ids_and_mutable_defaults() -> None:
    guild = await GuildSettings.create(1)
    user = await UserSettings.create(1)
    guild.disabled_domains.append(DomainId.YOUTUBE)
    user.proxy_tags.append(ProxyTag(prefix="[", suffix="]"))
    user.fix_mode = FixMode.RESEND
    await guild.save()
    await user.save()
    other_guild = await GuildSettings.create(2)
    other_user = await UserSettings.create(2)
    assert other_guild.disabled_domains == []
    assert other_user.proxy_tags == []
    saved_user = await UserSettings.get_or_none(1)
    assert saved_user is not None
    assert saved_user.proxy_tags == [ProxyTag(prefix="[", suffix="]")]
    assert saved_user.fix_mode is FixMode.RESEND
    saved_guild = await GuildSettings.get_or_none(1)
    assert saved_guild is not None
    assert saved_guild.disabled_domains == [DomainId.YOUTUBE]
    assert saved_guild.fix_mode is FixMode.DELETE_AND_RESEND


@pytest.mark.parametrize("settings_class", [GuildSettings, UserSettings])
@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ({"reply_instead_of_delete": True}, FixMode.REPLY),
        ({"reply_instead_of_delete": True, "fix_mode": "resend"}, FixMode.RESEND),
        (
            {"reply_instead_of_delete": False, "fix_mode": "delete_and_resend"},
            FixMode.DELETE_AND_RESEND,
        ),
    ],
)
def test_legacy_reply_setting_migrates_without_overriding_explicit_choice(
    settings_class: type[GuildSettings] | type[UserSettings],
    values: dict[str, object],
    expected: FixMode,
) -> None:
    settings = settings_class.model_validate({"id": 1, **values})
    assert settings.fix_mode is expected
    assert "reply_instead_of_delete" not in settings.model_dump()


@pytest.mark.usefixtures("db")
async def test_saved_legacy_json_migrates_when_read_and_is_normalized_on_save() -> None:
    await UserSettingsTable.create(id=1, data={"reply_instead_of_delete": True, "lang": "fr"})
    user = await UserSettings.get_or_none(1)
    assert user is not None
    assert user.fix_mode is FixMode.REPLY
    await user.save()
    assert (await UserSettingsTable.get(id=1)).data["fix_mode"] == "reply"
    assert "reply_instead_of_delete" not in (await UserSettingsTable.get(id=1)).data


@pytest.mark.parametrize("settings_class", [GuildSettings, UserSettings])
def test_invalid_fix_modes_are_rejected(
    settings_class: type[GuildSettings] | type[UserSettings],
) -> None:
    with pytest.raises(ValidationError, match="fix_mode"):
        settings_class.model_validate({"id": 1, "fix_mode": "invalid"})


@pytest.mark.parametrize(
    ("line", "prefix", "suffix", "content", "mismatch"),
    [
        ("[text]", "[", "]", " [hello] ", "[hello"),
        (":cat text", ":cat", "", ":cat hello", "hello :cat"),
        ("text :) ", "", ":)", "hello :)", ":) hello"),
        ("context text !", "context", "!", "context hello !", "other hello !"),
    ],
)
def test_proxy_tag_parsing_and_matching(
    line: str, prefix: str, suffix: str, content: str, mismatch: str
) -> None:
    tag = ProxyTag.from_line(line)
    assert tag.prefix == prefix
    assert tag.suffix == suffix
    assert tag.matches(content)
    assert not tag.matches(mismatch)
    assert ProxyTag.from_line(tag.to_line()) == tag


@pytest.mark.parametrize("line", ["", "text", " text ", "no placeholder", "[TEXT]"])
def test_invalid_proxy_tags_are_rejected(line: str) -> None:
    with pytest.raises(ValueError, match=f"^{re.escape(line)}$") as error:
        ProxyTag.from_line(line)
    assert error.value.args == (line,)


@pytest.mark.usefixtures("db")
async def test_ignore_me_is_idempotent_and_toggle_reports_new_state() -> None:
    assert not await IgnoreMe.contains(1)
    await IgnoreMe.remove(1)
    await IgnoreMe.add(1)
    await IgnoreMe.add(1)
    assert await IgnoreMe.filter(id=1).count() == 1
    assert await IgnoreMe.contains(1)
    assert not await IgnoreMe.toggle(1)
    assert not await IgnoreMe.contains(1)
    assert await IgnoreMe.toggle(1)
    assert await IgnoreMe.contains(1)


@pytest.mark.usefixtures("db")
async def test_fix_service_selection_is_unique_per_guild_domain_and_method() -> None:
    guild = await GuildSettingsTable.create(id=1)
    await GuildFixMethod.create(guild=guild, domain_id=DomainId.TWITTER, fix_id=1)
    await GuildFixMethod.create(guild=guild, domain_id=DomainId.TWITTER, fix_id=2)
    with pytest.raises(IntegrityError):
        await GuildFixMethod.create(guild=guild, domain_id=DomainId.TWITTER, fix_id=1)
    selected = await GuildFixMethod.get(guild_id=1, fix_id=1)
    assert selected.domain_id is DomainId.TWITTER
    await guild.delete()
    assert await GuildFixMethod.all().count() == 0


@pytest.mark.usefixtures("db")
async def test_fixed_messages_and_sponsor_records_persist() -> None:
    await FixedMessage.create(id=1, guild_id=2, channel_id=3, author_id=4, send_type="webhook")
    message = await FixedMessage.get(id=1)
    assert (message.guild_id, message.channel_id, message.author_id, message.send_type) == (
        2,
        3,
        4,
        "webhook",
    )
    assert message.created_at.utcoffset() is not None
    sponsor = await SponsoredGuild.create(id=2, sponsor_id=None)
    assert (await SponsoredGuild.get(id=2)).sponsor_id is None
    sponsor.sponsor_id = 10
    await sponsor.save()
    assert (await SponsoredGuild.get(id=2)).sponsor_id == 10


@pytest.mark.usefixtures("db")
async def test_legacy_settings_string_includes_stored_values() -> None:
    old = await GuildSettingsOld.create(id=123, lang="en_US", bot_visibility=True)
    assert "GuildSettingsOld(" in str(old)
    assert "id=123" in str(old)
    assert "lang='en_US'" in str(old)
    assert "bot_visibility=True" in str(old)


def test_setting_names_are_unique_and_fix_modes_are_stable() -> None:
    assert len({setting.value for setting in GuildSetting}) == len(GuildSetting)
    assert len({setting.value for setting in UserSetting}) == len(UserSetting)
    assert {mode.value for mode in FixMode} == {"delete_and_resend", "reply", "resend"}
