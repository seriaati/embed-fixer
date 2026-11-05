from __future__ import annotations

from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from embed_fixer.fixes import DOMAINS, EXTRACTABLE_DOMAIN_IDS
from embed_fixer.models import GuildFixMethod, GuildSettings
from embed_fixer.settings import GuildSetting
from embed_fixer.ui import components as ui
from embed_fixer.ui import guild_settings as gs
from embed_fixer.ui.common import SettingsToggleButton
from tests.support.ui import emojis, guild, interaction

if TYPE_CHECKING:
    from typing import Any, Literal


@pytest.mark.parametrize(
    ("raw", "expected"), [("", None), ("   ", None), ("1", 1), (" 60 ", 60), ("3600", 3600)]
)
def test_reaction_seconds_parse_boundaries(raw: str, expected: int | None) -> None:
    assert gs.RemoveReactionsAfterModal._parse_seconds(raw) == expected


@pytest.mark.parametrize("raw", ["0", "3601", "-1", "1.5", "abc"])
def test_reaction_seconds_rejects_invalid_values(raw: str) -> None:
    with pytest.raises(ValueError, match=r".*"):
        gs.RemoveReactionsAfterModal._parse_seconds(raw)


@pytest.mark.usefixtures("db")
async def test_emoji_modal_prefills_and_persists_custom_emoji() -> None:
    settings = await GuildSettings.create(100)
    modal = gs.DeleteMsgEmojiModal(settings=settings)
    assert modal.emoji.component.default == "❌"
    modal.emoji.component._value = "<:custom:12345678>"
    i = interaction()
    await modal.on_submit(i)
    assert (await GuildSettings.get_or_create(100))[0].delete_msg_emoji == "<:custom:12345678>"
    assert "<:custom:12345678>" in i.response.send_message.await_args.kwargs["content"]
    assert i.response.send_message.await_args.kwargs["ephemeral"]


@pytest.mark.usefixtures("db")
async def test_reaction_seconds_modal_saves_timers_and_blank_disables() -> None:
    settings = await GuildSettings.create(100)
    settings.remove_delete_reaction_after = 60
    await settings.save()
    modal = gs.RemoveReactionsAfterModal(settings=settings)
    assert modal.delete_seconds.component.default == "60"
    assert modal.rotate_seconds.component.default is None
    modal.delete_seconds.component._value = ""
    modal.rotate_seconds.component._value = "3600"
    i = interaction()
    await modal.on_submit(i)
    updated = (await GuildSettings.get_or_create(100))[0]
    assert updated.remove_delete_reaction_after is None
    assert updated.remove_rotate_reaction_after == 3600
    assert "3600" in i.response.send_message.await_args.kwargs["content"]


@pytest.mark.usefixtures("db")
@pytest.mark.parametrize(("delete", "rotate"), [("x", "5"), ("5", "3601")])
async def test_reaction_seconds_modal_invalid_input_is_atomic(delete: str, rotate: str) -> None:
    settings = await GuildSettings.create(100)
    modal = gs.RemoveReactionsAfterModal(settings=settings)
    modal.delete_seconds.component._value = delete
    modal.rotate_seconds.component._value = rotate
    i = interaction()
    await modal.on_submit(i)
    assert (await GuildSettings.get_or_create(100))[0].remove_delete_reaction_after is None
    assert "3600" in i.response.send_message.await_args.kwargs["content"]


async def test_pagination_clamps_pages_and_domain_requires_known_id() -> None:
    view = gs.GuildSettingsView(guild=guild(), lang=None, app_emojis=emojis())
    assert view.page_item_ids == ()
    view.item_ids = list(range(23))
    view.page = 99
    assert view.page_item_ids == (20, 21, 22)
    assert view.page == 2
    view.page = -2
    assert view.page_item_ids == tuple(range(10))
    assert view.page == 0
    with pytest.raises(ValueError, match="Domain ID is not set"):
        _ = view.domain
    with pytest.raises(ValueError, match="Domain ID is not set"):
        await view._get_current_fix()
    with pytest.raises(ValueError, match="Domain ID is not set"):
        await view._get_domain_text_display()
    cast("Any", view).domain_id = 999
    with pytest.raises(ValueError, match="Invalid domain ID"):
        _ = view.domain


@pytest.mark.usefixtures("db")
@pytest.mark.parametrize(
    "setting",
    [
        setting
        for setting in GuildSetting
        if setting not in {GuildSetting.DELETE_MSG_EMOJI, GuildSetting.REMOVE_REACTIONS_AFTER}
    ],
)
async def test_every_guild_screen_renders_real_components(setting: GuildSetting) -> None:
    server = guild(channel_ids=(10, 11))
    server.roles = [MagicMock(id=20, mention="<@&20>")]
    settings = await GuildSettings.create(100)
    for attr in gs.MULTI_CHANNEL_SETTING_ATTRS.values():
        setattr(settings, attr, [10, 11])
    settings.whitelist_role_ids = [20]
    await settings.save()
    view = gs.GuildSettingsView(guild=server, lang="en_US", app_emojis=emojis())
    i = interaction()
    await view.start(i, setting=setting)
    assert len(view.children) == 1
    i.response.defer.assert_awaited_once_with(ephemeral=True)
    i.followup.send.assert_awaited_once_with(view=view, ephemeral=True)
    assert view.message is i.original_response.return_value
    container = view.children[0]
    assert isinstance(container, ui.Container)
    assert container.children
    if setting in gs.TOGGLE_SETTING_ATTRS:
        sections = [child for child in container.children if isinstance(child, discord.ui.Section)]
        assert len(sections) == 1
        button = sections[0].accessory
        assert isinstance(button, SettingsToggleButton)
        assert button.settings_key == gs.TOGGLE_SETTING_ATTRS[setting]
        assert isinstance(button, gs.SponsorToggleButton) == (setting in gs.SPONSOR_ONLY_SETTINGS)
    if setting in gs.MULTI_CHANNEL_SETTING_ATTRS:
        assert view.item_ids == [10, 11]
        assert view.item_type == "channel"
    if setting in gs.ROLE_SETTING_ATTRS:
        assert view.item_ids == [20]
        assert view.item_type == "role"


@pytest.mark.usefixtures("db")
async def test_unknown_screen_rejects_and_stale_channels_are_pruned() -> None:
    settings = await GuildSettings.create(100)
    for attr in ("extract_media_channels", "disable_fix_channels", "disable_image_spoilers"):
        setattr(settings, attr, [10, 99, 12])
    await settings.save()
    server = guild(channel_ids=(10,))
    server.threads = [MagicMock(id=12)]
    view = gs.GuildSettingsView(guild=server, lang=None, app_emojis=emojis())
    await view._remove_invalid_channels(settings)
    assert settings.extract_media_channels == [10, 12]
    assert (await GuildSettings.get_or_create(100))[0].disable_image_spoilers == [10, 12]
    with pytest.raises(ValueError, match="Unknown setting"):
        await view.start(interaction(), setting=cast("Any", "unknown"))


@pytest.mark.usefixtures("db")
async def test_channel_and_role_paging_refreshes_visible_mentions() -> None:
    server = guild(channel_ids=tuple(range(1, 24)))
    server.roles = [MagicMock(id=n, mention=f"<@&{n}>") for n in range(1, 24)]
    settings = await GuildSettings.create(100)
    settings.extract_media_channels = list(range(1, 24))
    settings.whitelist_role_ids = list(range(1, 24))
    await settings.save()
    for setting, mention in (
        (GuildSetting.EXTRACT_MEDIA_CHANNELS, "<#11>"),
        (GuildSetting.WHITELIST_ROLE_IDS, "<@&11>"),
    ):
        view = gs.GuildSettingsView(guild=server, lang="en_US", app_emojis=emojis())
        await view.start(interaction(), setting=setting)
        next_button = next(
            child for child in view.walk_children() if isinstance(child, gs.NextButton)
        )
        previous = next(
            child for child in view.walk_children() if isinstance(child, gs.PreviousButton)
        )
        i = interaction()
        await next_button.callback(i)
        assert view.page == 1
        assert isinstance(view.children[0], ui.Container)
        field = view.find_child_by_id(
            view.children[0], item_type=discord.ui.TextDisplay, item_id=gs.SELECTED_ITEMS_TEXT_ID
        )
        assert field is not None
        assert mention in field.content
        await previous.callback(i)
        assert view.page == 0
        await previous.callback(i)
        assert view.page == 0
        assert view.children[0].children[-1].id == gs.PAGINATOR_ACTION_ROW_ID


@pytest.mark.usefixtures("db")
async def test_disable_domains_models_default_opt_in_and_extractable_domains() -> None:
    select = gs.DisableDomainSelect([], [])
    assert len(select.options) == len(DOMAINS)
    for domain, option in zip(DOMAINS, select.options, strict=True):
        assert option.default is not domain.enabled_by_default
    youtube = next(domain for domain in DOMAINS if not domain.enabled_by_default)
    selected = [DOMAINS[0].id.value]
    select._values = [str(value) for value in selected]
    await select.callback(interaction())
    settings = (await GuildSettings.get_or_create(100))[0]
    assert settings.disabled_domains == selected
    assert youtube.id.value in settings.enabled_domains
    extract = gs.DisableExtractMediaDomainSelect(selected)
    assert {int(option.value) for option in extract.options} == {
        d.value for d in EXTRACTABLE_DOMAIN_IDS
    }
    extract._values = [str(next(iter(EXTRACTABLE_DOMAIN_IDS)).value)]
    await extract.callback(interaction())
    assert (await GuildSettings.get_or_create(100))[0].disable_extract_media_domains == [
        int(extract.values[0])
    ]
    for selector in (select, extract):
        i = interaction(guild_id=None)
        await selector.callback(i)
        i.response.defer.assert_not_awaited()


@pytest.mark.usefixtures("db")
async def test_guild_language_callback_uses_guild_identity() -> None:
    view = gs.GuildSettingsView(guild=guild(), lang="en_US", app_emojis=emojis())
    select = gs.LangSelector(current="en_US")
    view.add_item(discord.ui.ActionRow(select))
    select._values = ["ja_JP"]
    await select.callback(interaction())
    assert (await GuildSettings.get_or_create(100))[0].lang == "ja_JP"
    assert await GuildSettings.get_or_none(200) is None


@pytest.mark.usefixtures("db")
@pytest.mark.parametrize("select_type", ["single", "multiple"])
async def test_channel_select_saves_toggle_add_remove_and_empty(
    select_type: Literal["single", "multiple"],
) -> None:
    settings = await GuildSettings.create(100)
    settings.extract_media_channels = [10]
    settings.funnel_target_channel = 10
    await settings.save()
    view = gs.GuildSettingsView(
        guild=guild(channel_ids=(10, 11)), lang="en_US", app_emojis=emojis()
    )
    attr = "funnel_target_channel" if select_type == "single" else "extract_media_channels"
    select = gs.ChannelSelect(attr, select_type=select_type)
    container = ui.Container(discord.ui.ActionRow(select))
    view.add_item(container)
    assert discord.ChannelType.forum not in select.channel_types
    select._values = (
        [MagicMock(id=10), MagicMock(id=11)] if select_type == "multiple" else [MagicMock(id=11)]
    )
    i = interaction()
    await select.callback(i)
    settings = (await GuildSettings.get_or_create(100))[0]
    assert getattr(settings, attr) == ([11] if select_type == "multiple" else 11)
    if select_type == "multiple":
        assert view.item_ids == [11]
        assert i.edit_original_response.await_count == 1
    else:
        assert select.default_values[0].id == 11
        select._values = []
        await select.callback(i)
        assert (await GuildSettings.get_or_create(100))[0].funnel_target_channel is None
        assert select.default_values == []


@pytest.mark.usefixtures("db")
async def test_role_select_toggles_roles_and_hard_rerender_handles_both_response_states() -> None:
    settings = await GuildSettings.create(100)
    settings.whitelist_role_ids = [10]
    await settings.save()
    server = guild()
    server.roles = [MagicMock(id=11, mention="<@&11>")]
    view = gs.GuildSettingsView(guild=server, lang="en_US", app_emojis=emojis())
    select = gs.RoleSelect("whitelist_role_ids")
    view.add_item(ui.Container(discord.ui.ActionRow(select)))
    select._values = [MagicMock(id=10), MagicMock(id=11)]
    i = interaction()
    await select.callback(i)
    assert (await GuildSettings.get_or_create(100))[0].whitelist_role_ids == [11]
    assert view.page == 0
    i.response.edit_message.assert_awaited_once()
    i.response.is_done.return_value = True
    i.response.edit_message.reset_mock()
    await view._hard_rerender(i)
    i.response.edit_message.assert_not_awaited()
    assert i.edit_original_response.await_count == 3


@pytest.mark.usefixtures("db")
async def test_domain_and_fix_selectors_persist_choices_and_replace_selected_state() -> None:
    view = gs.GuildSettingsView(guild=guild(), lang="en_US", app_emojis=emojis())
    await view.start(interaction(), setting=GuildSetting.CHOOSE_FIX_SERVICE)
    selector = next(child for child in view.walk_children() if isinstance(child, gs.DomainSelector))
    target = next(
        domain for domain in DOMAINS if len(domain.fix_methods) > 1 and domain.id != DOMAINS[0].id
    )
    selector._values = [str(target.id.value)]
    i = interaction()
    await selector.callback(i)
    assert view.domain_id == target.id
    assert [option.value for option in selector.options if option.default] == [str(target.id.value)]
    method = target.fix_methods[-1]
    fix_selector = next(
        child for child in view.walk_children() if isinstance(child, gs.FixMethodSelector)
    )
    fix_selector._values = [str(method.id)]
    await fix_selector.callback(i)
    stored = await GuildFixMethod.get(guild_id=100, domain_id=target.id)
    assert stored.fix_id == method.id
    replacement = next(
        child for child in view.walk_children() if isinstance(child, gs.FixMethodSelector)
    )
    assert replacement is not fix_selector
    assert [option.value for option in replacement.options if option.default] == [str(method.id)]
    assert method.name in (await view._get_domain_text_display()).content
    stored.fix_id = 99999
    await stored.save()
    assert target.default_fix_method is not None
    assert target.default_fix_method.name in (await view._get_domain_text_display()).content


@pytest.mark.usefixtures("db")
async def test_domain_display_without_default_rejects() -> None:
    empty = next(domain for domain in DOMAINS if not domain.fix_methods)
    view = gs.GuildSettingsView(guild=guild(), lang="en_US", app_emojis=emojis())
    view.domain_id = empty.id
    with pytest.raises(ValueError, match="has no default fix method"):
        await view._get_domain_text_display()


@pytest.mark.usefixtures("db")
@pytest.mark.parametrize("unlock", [False, True])
async def test_sponsor_toggle_requires_guild_administrator_sponsorship(
    monkeypatch: pytest.MonkeyPatch, *, unlock: bool
) -> None:
    sponsors = MagicMock(unlock_guild=AsyncMock(return_value=unlock), remove_guild=AsyncMock())
    monkeypatch.setattr(gs, "sponsors", sponsors)
    button = gs.SponsorToggleButton(
        value=False, app_emojis={}, settings_key="hide_webhook_suffix", settings_type="guild"
    )
    i = interaction()
    assert await button.before_toggle(i, value=True) is unlock
    sponsors.unlock_guild.assert_awaited_once_with(i.guild)
    assert i.followup.send.await_count == int(not unlock)
    assert await button.before_toggle(i, value=False)
    sponsors.remove_guild.assert_awaited_once_with(100)
    assert not await button.before_toggle(interaction(guild_id=None), value=True)


async def test_page_refresh_without_item_type_edits_existing_view() -> None:
    view = gs.GuildSettingsView(guild=guild(), lang="en_US", app_emojis=emojis())
    container = ui.Container(discord.ui.TextDisplay("unchanged"))
    view.add_item(container)
    i = interaction()
    await view._update_page(i)
    assert len(container.children) == 1
    i.response.edit_message.assert_awaited_once_with(view=view)
