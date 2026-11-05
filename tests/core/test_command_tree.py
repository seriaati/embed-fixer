from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

from discord import app_commands

from embed_fixer.core.command_tree import CommandTree
from tests.support.ui import interaction

if TYPE_CHECKING:
    import pytest


async def test_command_tree_captures_then_uses_discord_error_handler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[Exception] = []
    monkeypatch.setattr("embed_fixer.core.command_tree.capture_exception", captured.append)
    base = AsyncMock()
    monkeypatch.setattr(app_commands.CommandTree, "on_error", base)
    tree = object.__new__(CommandTree)
    i = interaction()
    error = app_commands.AppCommandError("broken")
    await tree.on_error(i, error)
    assert captured == [error]
    base.assert_awaited_once_with(i, error)
