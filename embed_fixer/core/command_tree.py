from __future__ import annotations

from typing import TYPE_CHECKING

from discord import app_commands

from embed_fixer.utils.misc import capture_exception

if TYPE_CHECKING:
    from embed_fixer.bot import Interaction


class CommandTree(app_commands.CommandTree):
    async def on_error(self, i: Interaction, error: app_commands.AppCommandError) -> None:
        capture_exception(error)
        return await super().on_error(i, error)
