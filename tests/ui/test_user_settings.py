from __future__ import annotations

import discord
import pytest

from embed_fixer.models import ProxyTag, UserSettings
from embed_fixer.settings import UserSetting
from embed_fixer.ui.common import (
    FixModeSelector,
    LangSelector,
    SettingsSection,
    SettingsToggleButton,
)
from embed_fixer.ui.user_settings import (
    MAX_PROXY_TAGS,
    ProxyTagsButton,
    ProxyTagsModal,
    UserSettingsView,
)
from tests.support.ui import interaction


def test_user_screen_renders_all_settings_and_proxy_editor() -> None:
    settings = UserSettings(id=200, notify_on_react=True, lang="en_US")
    view = UserSettingsView(app_emojis={}, settings=settings, lang="en_US")
    sections = [item for item in view.walk_children() if isinstance(item, SettingsSection)]
    buttons = [
        section.accessory
        for section in sections
        if isinstance(section.accessory, SettingsToggleButton)
    ]
    assert {button.settings_key for button in buttons} == {
        setting.value
        for setting in UserSetting
        if setting not in {UserSetting.LANG, UserSetting.FIX_MODE}
    }
    assert buttons[0].value
    assert sum(isinstance(item, FixModeSelector) for item in view.walk_children()) == 1
    assert sum(isinstance(item, LangSelector) for item in view.walk_children()) == 1
    assert sum(isinstance(item, ProxyTagsButton) for item in view.walk_children()) == 1
    assert sum(isinstance(item, discord.ui.Separator) for item in view.walk_children()) == 3


@pytest.mark.usefixtures("db")
async def test_proxy_editor_button_fetches_current_settings() -> None:
    settings = await UserSettings.create(200)
    settings.proxy_tags = [ProxyTag(prefix="[", suffix="]")]
    await settings.save()
    button = ProxyTagsButton(label="Edit")
    i = interaction()
    await button.callback(i)
    modal = i.response.send_modal.await_args.args[0]
    assert isinstance(modal, ProxyTagsModal)
    assert modal.tags.component.default == "[ text ]"
    assert modal.tags.description


@pytest.mark.usefixtures("db")
@pytest.mark.parametrize("raw", ["[text]\n\n:cgg text", "", " \n\n"])
async def test_proxy_modal_saves_valid_tags_and_empty_clears(raw: str) -> None:
    settings = await UserSettings.create(200)
    settings.proxy_tags = [ProxyTag(prefix="old", suffix="")]
    await settings.save()
    modal = ProxyTagsModal(settings=settings)
    modal.tags.component._value = raw
    i = interaction()
    await modal.on_submit(i)
    stored = (await UserSettings.get_or_create(200))[0]
    assert [tag.to_line() for tag in stored.proxy_tags] == (
        ["[ text ]", ":cgg text"] if raw.strip() else []
    )
    assert i.response.send_message.await_args.kwargs["ephemeral"]


@pytest.mark.usefixtures("db")
@pytest.mark.parametrize(
    "raw", ["[text]\ninvalid", "text", "\n".join(["[text]"] * (MAX_PROXY_TAGS + 1))]
)
async def test_proxy_modal_validation_preserves_saved_tags(raw: str) -> None:
    settings = await UserSettings.create(200)
    settings.proxy_tags = [ProxyTag(prefix="old", suffix="")]
    await settings.save()
    modal = ProxyTagsModal(settings=settings)
    modal.tags.component._value = raw
    i = interaction()
    await modal.on_submit(i)
    assert (await UserSettings.get_or_create(200))[0].proxy_tags == settings.proxy_tags
    assert i.response.send_message.await_args.args[0] != modal.translate("proxy_tags_saved")


@pytest.mark.usefixtures("db")
async def test_proxy_modal_accepts_maximum_tag_count() -> None:
    modal = ProxyTagsModal(settings=UserSettings(id=200))
    modal.tags.component._value = "\n".join(f"prefix{n} text" for n in range(MAX_PROXY_TAGS))
    await modal.on_submit(interaction())
    assert len((await UserSettings.get_or_create(200))[0].proxy_tags) == MAX_PROXY_TAGS
