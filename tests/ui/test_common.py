from __future__ import annotations

from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock

if TYPE_CHECKING:
    from typing import Any, Literal

import discord
import pytest

from embed_fixer.models import GuildSettings, UserSettings
from embed_fixer.settings import FixMode
from embed_fixer.ui import components as ui
from embed_fixer.ui.common import (
    FOLLOW_GUILD_VALUE,
    FixModeSelector,
    LangSelector,
    SettingsSection,
    SettingsToggleButton,
)
from tests.support.ui import interaction


@pytest.mark.usefixtures("db")
@pytest.mark.parametrize("mode", list(FixMode))
@pytest.mark.parametrize("settings_type", ["guild", "user"])
async def test_fix_mode_selection_persists_and_updates_defaults(
    mode: FixMode, settings_type: Literal["guild", "user"]
) -> None:
    select = FixModeSelector(current=None, lang="en_US", settings_type=settings_type)
    view = ui.View(lang="en_US")
    view.add_item(select)
    select._values = [mode.value]
    i = interaction()
    await select.callback(i)
    settings = await (GuildSettings if settings_type == "guild" else UserSettings).get_or_none(
        100 if settings_type == "guild" else 200
    )
    assert settings is not None
    assert settings.fix_mode == mode
    assert [option.value for option in select.options if option.default] == [mode.value]
    i.response.edit_message.assert_awaited_once_with(view=view)


@pytest.mark.usefixtures("db")
async def test_user_fix_mode_can_follow_guild_and_guild_selector_ignores_dm() -> None:
    user = await UserSettings.create(200)
    user.fix_mode = FixMode.REPLY
    await user.save()
    select = FixModeSelector(current=user.fix_mode, lang="en_US", settings_type="user")
    select._values = [FOLLOW_GUILD_VALUE]
    await select.callback(interaction())
    assert (await UserSettings.get_or_create(200))[0].fix_mode is None
    guild = FixModeSelector(current=FixMode.REPLY, lang="en_US", settings_type="guild")
    guild._values = [FixMode.REPLY.value]
    i = interaction(guild_id=None)
    await guild.callback(i)
    i.response.edit_message.assert_not_awaited()


@pytest.mark.usefixtures("db")
@pytest.mark.parametrize("settings_type", ["guild", "user"])
async def test_toggle_persists_each_click_and_styles(
    settings_type: Literal["guild", "user"],
) -> None:
    key = "disable_webhook_reply" if settings_type == "guild" else "notify_on_react"
    button = SettingsToggleButton(
        value=False, app_emojis={}, settings_key=key, settings_type=settings_type
    )
    assert button.label == "OFF"
    assert button.style == discord.ButtonStyle.gray
    view = ui.View(lang="en_US")
    view.add_item(button)
    i = interaction()
    for expected in (True, False):
        await button.callback(i)
        settings = await (GuildSettings if settings_type == "guild" else UserSettings).get_or_none(
            100 if settings_type == "guild" else 200
        )
        assert settings is not None
        assert getattr(settings, key) is expected
        assert button.value is expected
        assert button.label == ("ON" if expected else "OFF")
    assert i.edit_original_response.await_count == 2


@pytest.mark.usefixtures("db")
async def test_toggle_can_veto_and_ignores_guild_toggle_in_dm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    button = SettingsToggleButton(
        value=False, app_emojis={}, settings_key="bot_visibility", settings_type="guild"
    )
    i = interaction(guild_id=None)
    await button.callback(i)
    i.response.defer.assert_not_awaited()
    veto = AsyncMock(return_value=False)
    monkeypatch.setattr(button, "before_toggle", veto)
    i = interaction()
    await button.callback(i)
    assert not button.value
    assert await GuildSettings.get_or_none(100) is None
    i.edit_original_response.assert_not_awaited()


def test_toggle_uses_application_emoji_and_sections_use_correct_heading() -> None:
    button = SettingsToggleButton(
        value=True,
        app_emojis=cast("Any", {"TOGGLE_ON": "✅"}),
        settings_key="value",
        settings_type="user",
    )
    assert button.label is None
    assert str(button.emoji) == "✅"
    for settings_type, heading in (("guild", "#"), ("user", "##")):
        section = SettingsSection(
            title="title",
            description="description",
            app_emojis={},
            value=False,
            settings_key="value",
            settings_type=cast("Literal['guild', 'user']", settings_type),
        )
        assert isinstance(section.children[0], discord.ui.TextDisplay)
        assert section.children[0].content == f"{heading} title\ndescription"
        assert isinstance(section.accessory, SettingsToggleButton)


@pytest.mark.usefixtures("db")
async def test_language_selector_saves_user_and_falls_back_to_defer() -> None:
    selector = LangSelector("en_US", settings_type="user")
    assert any(option.value == "en_US" and option.default for option in selector.options)
    selector._values = ["ja_JP"]
    i = interaction()
    await selector.callback(i)
    assert (await UserSettings.get_or_create(200))[0].lang == "ja_JP"
    i.response.defer.assert_awaited_once()


@pytest.mark.usefixtures("db")
@pytest.mark.parametrize("hard_rerender", [False, True])
async def test_language_selector_replaces_nested_selected_state(
    monkeypatch: pytest.MonkeyPatch, *, hard_rerender: bool
) -> None:
    selector = LangSelector("en_US", settings_type="user")
    row = discord.ui.ActionRow(selector, id=9)
    container = ui.Container(row)
    view = ui.LayoutView(lang="en_US")
    view.add_item(container)
    rerender = AsyncMock()
    if hard_rerender:
        monkeypatch.setattr(view, "_hard_rerender", rerender, raising=False)
    selector._values = ["en_US"]
    i = interaction()
    await selector.callback(i)
    replacement = container.children[0]
    assert replacement is not row
    assert isinstance(replacement, discord.ui.ActionRow)
    assert replacement.id == 9
    assert isinstance(replacement.children[0], LangSelector)
    assert replacement.children[0].options[0].value
    if hard_rerender:
        rerender.assert_awaited_once_with(i)
        i.response.defer.assert_not_awaited()
    else:
        i.response.defer.assert_awaited_once()


@pytest.mark.usefixtures("db")
async def test_shared_guild_language_selector_persists_under_guild_identity() -> None:
    selector = LangSelector("en_US", settings_type="guild")
    selector._values = ["ja_JP"]
    await selector.callback(interaction(guild_id=100, user_id=200))
    settings = await GuildSettings.get_or_none(100)
    assert settings is not None
    assert settings.lang == "ja_JP"
    assert await GuildSettings.get_or_none(200) is None


@pytest.mark.usefixtures("db")
async def test_shared_guild_language_selector_ignores_missing_guild_identity() -> None:
    selector = LangSelector("en_US", settings_type="guild")
    selector._values = ["ja_JP"]
    i = interaction(guild_id=None, user_id=200)
    await selector.callback(i)
    assert await GuildSettings.get_or_none(200) is None
    assert await UserSettings.get_or_none(200) is None
    i.response.defer.assert_not_awaited()


@pytest.mark.usefixtures("db")
async def test_language_selector_stale_layout_callback_defers_without_matching_row() -> None:
    selector = LangSelector("en_US", settings_type="user")
    view = ui.LayoutView(lang="en_US")
    view.add_item(ui.Container(discord.ui.TextDisplay("other settings")))
    selector._view = view
    selector._values = ["en_US"]
    i = interaction()
    await selector.callback(i)
    i.response.defer.assert_awaited_once()
