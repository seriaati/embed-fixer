from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

import discord
from discord import ui

if TYPE_CHECKING:
    from ..translator import Translator


class View(ui.View):
    def __init__(
        self, author: discord.Member | discord.User, guild: discord.Guild, translator: Translator
    ) -> None:
        super().__init__(timeout=600)

        self.author = author
        self.message: discord.Message | None = None
        self.guild = guild
        self.translator = translator
        self.lang = guild.preferred_locale.value if guild else "en-US"

    async def start(self) -> None:
        self.lang = await self.translator.get_guild_lang(self.guild)

    def translate(self, key: str, **kwargs: Any) -> str:
        return self.translator.get(self.lang, key, **kwargs)

    async def on_timeout(self) -> None:
        if self.message is None:
            return

        for child in self.children:
            if isinstance(child, ui.Select) or (isinstance(child, ui.Button) and child.url is None):
                child.disabled = True

        with contextlib.suppress(discord.NotFound):
            await self.message.edit(view=self)
