from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

import discord
from discord import ui

from embed_fixer.translator import DEFAULT_LANG

if TYPE_CHECKING:
    from ..translator import Translator


class View(ui.View):
    def __init__(self, guild: discord.Guild, translator: Translator) -> None:
        super().__init__(timeout=600)

        self.message: discord.Message | None = None
        self.guild = guild
        self.translator = translator
        self.lang = guild.preferred_locale.value if guild else DEFAULT_LANG

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

        with contextlib.suppress(discord.NotFound):
            await self.message.edit(view=self)


class Modal(ui.Modal):
    def __init__(self, guild: discord.Guild, translator: Translator, *, title: str) -> None:
        super().__init__(title=title, timeout=600)

        self.guild = guild
        self.translator = translator
        self.lang = guild.preferred_locale.value if guild else DEFAULT_LANG
        self.title = self.translate(title)

    def translate(self, key: str, **kwargs: Any) -> str:
        return self.translator.get(self.lang, key, **kwargs)
