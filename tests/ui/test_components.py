from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import discord
import pytest

from embed_fixer.ui import components as ui
from tests.support.ui import interaction

if TYPE_CHECKING:
    from typing import Any


@pytest.mark.parametrize("view_cls", [ui.View, ui.LayoutView])
async def test_views_defaults_translation_and_timeout(view_cls: Any) -> None:
    view = view_cls(lang=None)
    assert view.timeout == 600
    assert view.translate("reset_yes") == "Yes"
    await view.on_timeout()
    button = discord.ui.Button(label="save", custom_id="save")
    link = discord.ui.Button(label="link", url="https://example.com")
    select = discord.ui.Select(options=[discord.SelectOption(label="value")])
    view.add_item(button)
    view.add_item(link)
    view.add_item(select)
    assert view.get_item("save") is button
    assert view.get_item("missing") is None
    view.message = AsyncMock()
    await view.on_timeout()
    assert button.disabled
    assert select.disabled
    assert not link.disabled
    view.message.edit.assert_awaited_once_with(view=view)


@pytest.mark.parametrize("view_cls", [ui.View, ui.LayoutView])
async def test_view_timeout_ignores_deleted_message(view_cls: Any) -> None:
    view = view_cls(lang="en_US", timeout=12)
    view.message = AsyncMock()
    view.message.edit.side_effect = discord.NotFound(
        interaction().response, {"message": "deleted", "code": 10008}
    )
    await view.on_timeout()
    assert view.timeout == 12


@pytest.mark.parametrize("done", [False, True])
@pytest.mark.parametrize("is_modal", [False, True])
async def test_component_errors_capture_and_send_bounded_error(
    monkeypatch: pytest.MonkeyPatch, *, done: bool, is_modal: bool
) -> None:
    captured: list[Exception] = []
    monkeypatch.setattr(ui, "capture_exception", captured.append)
    owner: Any = ui.Modal(title_key="reset_confirm", lang=None) if is_modal else ui.View(lang=None)
    i = interaction()
    i.response.is_done.return_value = done
    error = ValueError("x" * 5000)
    if is_modal:
        await owner.on_error(i, error)
    else:
        await ui.ViewMixin.on_error(owner, i, error, discord.ui.Button())
    assert captured == [error]
    sender = i.followup.send if done else i.response.send_message
    assert sender.await_args.kwargs["ephemeral"]
    assert len(sender.await_args.kwargs["embed"].description) == 4096


def test_layout_find_remove_and_replace_preserve_order() -> None:
    first = discord.ui.TextDisplay("first", id=1)
    second = discord.ui.TextDisplay("second", id=2)
    third = discord.ui.TextDisplay("third", id=3)
    container = ui.Container(first, second, third)
    assert ui.LayoutView.find_child_by_id(container, item_type=discord.ui.Button, item_id=1) is None
    assert (
        ui.LayoutView.find_child_by_id(container, item_type=discord.ui.TextDisplay, item_id=2)
        is second
    )
    replacement = discord.ui.TextDisplay("new", id=4)
    assert ui.LayoutView.replace_child_by_id(
        container, item_type=discord.ui.TextDisplay, item_id=2, new_child=replacement
    )
    assert list(container.children) == [first, replacement, third]
    assert not ui.LayoutView.replace_child_by_id(
        container, item_type=discord.ui.TextDisplay, item_id=99, new_child=second
    )
    assert not ui.LayoutView.replace_child(container, old_child=second, new_child=second)
    assert (
        ui.LayoutView.remove_child_by_id(container, item_type=discord.ui.TextDisplay, item_id=4)
        is replacement
    )
    assert (
        ui.LayoutView.remove_child_by_id(container, item_type=discord.ui.TextDisplay, item_id=4)
        is None
    )
    view = ui.LayoutView(lang=None)
    view.add_item(first)
    view.add_item(third)
    assert view.replace_view_child(old_child=first, new_child=second)
    assert list(view.children) == [second, third]
    assert not view.replace_view_child(old_child=first, new_child=replacement)


@pytest.mark.parametrize("view_cls", [ui.View, ui.LayoutView])
@pytest.mark.parametrize("done", [False, True])
async def test_view_error_dispatch_uses_project_error_handler(
    monkeypatch: pytest.MonkeyPatch, view_cls: Any, *, done: bool
) -> None:
    captured: list[Exception] = []
    monkeypatch.setattr(ui, "capture_exception", captured.append)
    view = view_cls(lang="en_US")
    button = discord.ui.Button(label="broken")
    view.add_item(button)
    error = ValueError("x" * 5000)
    monkeypatch.setattr(button, "callback", AsyncMock(side_effect=error))
    i = interaction()
    i.response.is_done.return_value = done
    await view._scheduled_task(button, i)
    assert captured == [error]
    sender = i.followup.send if done else i.response.send_message
    other_sender = i.response.send_message if done else i.followup.send
    sender.assert_awaited_once()
    other_sender.assert_not_awaited()
    assert sender.await_args.kwargs["ephemeral"]
    assert sender.await_args.kwargs["embed"].description == "x" * 4096


@pytest.mark.parametrize(
    "select_cls",
    [
        discord.ui.Select,
        discord.ui.ChannelSelect,
        discord.ui.RoleSelect,
        discord.ui.UserSelect,
        discord.ui.MentionableSelect,
    ],
)
async def test_layout_timeout_disables_controls_nested_in_containers(select_cls: Any) -> None:
    button = discord.ui.Button(label="save")
    link = discord.ui.Button(label="link", url="https://example.com")
    select = (
        select_cls(options=[discord.SelectOption(label="value")])
        if select_cls is discord.ui.Select
        else select_cls()
    )
    section_button = discord.ui.Button(label="toggle")
    section_link = discord.ui.Button(label="help", url="https://example.com/help")
    view = ui.LayoutView(lang="en_US")
    view.add_item(
        ui.Container(
            discord.ui.ActionRow(button, link),
            discord.ui.ActionRow(select),
            discord.ui.Section(discord.ui.TextDisplay("setting"), accessory=section_button),
            discord.ui.Section(discord.ui.TextDisplay("help"), accessory=section_link),
        )
    )
    view.message = AsyncMock()
    await view.on_timeout()
    assert button.disabled
    assert select.disabled
    assert section_button.disabled
    assert not link.disabled
    assert not section_link.disabled
    view.message.edit.assert_awaited_once_with(view=view)
