from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

import discord
from discord import ui
from loguru import logger

from embed_fixer.core.translator import DEFAULT_LANG
from embed_fixer.utils.embed import ErrorEmbed
from embed_fixer.utils.misc import capture_exception

if TYPE_CHECKING:
    from embed_fixer.bot import Interaction
    from embed_fixer.core.translator import Translator


class View(ui.View):
    def __init__(self, guild: discord.Guild, translator: Translator) -> None:
        super().__init__(timeout=600)

        self.message: discord.Message | None = None
        self.guild = guild
        self.translator = translator
        self.lang = guild.preferred_locale.value if guild else DEFAULT_LANG

    async def on_error(self, i: Interaction, error: Exception, _item: ui.Item) -> None:
        logger.warning(f"Error in view {self.__class__.__name__}: {error}")
        capture_exception(error)

        if i.response.is_done():
            await i.followup.send(
                embed=ErrorEmbed(title="Error", description=str(error)[:4096]), ephemeral=True
            )
        else:
            await i.response.send_message(
                embed=ErrorEmbed(title="Error", description=str(error)[:4096]), ephemeral=True
            )

    async def start(self) -> None:
        self.lang = await self.translator.get_guild_lang(self.guild)

    def translate(self, key: str, **kwargs: Any) -> str:
        return self.translator.get(self.lang, key, **kwargs)

    def get_item(self, item_id: str) -> ui.Item | None:
        for item in self.children:
            if item.custom_id == item_id:  # pyright: ignore[reportAttributeAccessIssue]
                return item
        return None

    async def on_timeout(self) -> None:
        if self.message is None:
            return

        for child in self.children:
            if isinstance(child, ui.Select) or (isinstance(child, ui.Button) and child.url is None):
                child.disabled = True

        with contextlib.suppress(discord.NotFound, discord.HTTPException):
            await self.message.edit(view=self)


class Modal(ui.Modal):
    def __init__(self, guild: discord.Guild, translator: Translator, *, title: str) -> None:
        super().__init__(title=title, timeout=600)

        self.guild = guild
        self.translator = translator
        self.lang = guild.preferred_locale.value if guild else DEFAULT_LANG
        self.title = self.translate(title)

    async def on_error(self, i: Interaction, error: Exception) -> None:
        capture_exception(error)

        if i.response.is_done():
            await i.followup.send(
                embed=ErrorEmbed(title="Error", description=str(error)[:4096]), ephemeral=True
            )
        else:
            await i.response.send_message(
                embed=ErrorEmbed(title="Error", description=str(error)[:4096]), ephemeral=True
            )

    def translate(self, key: str, **kwargs: Any) -> str:
        return self.translator.get(self.lang, key, **kwargs)
