from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

import discord
from discord import ui
from discord.ui.view import BaseView
from loguru import logger

from embed_fixer.core.translator import DEFAULT_LANG, translator
from embed_fixer.utils.embed import ErrorEmbed
from embed_fixer.utils.misc import capture_exception

if TYPE_CHECKING:
    from embed_fixer.bot import Interaction


class ViewMixin:
    children: list[discord.ui.Item[Any]]
    message: discord.Message | None
    lang: str | None

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

    def get_item(self, item_id: str) -> ui.Item | None:
        for item in self.children:
            if item.custom_id == item_id:  # pyright: ignore[reportAttributeAccessIssue]
                return item
        return None

    def translate(self, key: str, **kwargs: Any) -> str:
        return translator.translate(key, lang=self.lang or DEFAULT_LANG, **kwargs)


class View(ui.View, ViewMixin):
    def __init__(self, *, lang: str | None, timeout: float | None = None) -> None:
        super().__init__(timeout=timeout or 600)

        self.message: discord.Message | None = None
        self.lang = lang

    async def on_timeout(self) -> None:
        if self.message is None:
            return

        for child in self.children:
            if isinstance(child, ui.Select) or (isinstance(child, ui.Button) and child.url is None):
                child.disabled = True

        with contextlib.suppress(discord.NotFound, discord.HTTPException):
            await self.message.edit(view=self)


class LayoutView(ui.LayoutView, ViewMixin):
    def __init__(self, *, lang: str | None, timeout: float | None = None) -> None:
        super().__init__(timeout=timeout or 600)

        self.message: discord.Message | None = None
        self.lang = lang

    async def on_timeout(self) -> None:
        if self.message is None:
            return

        for child in self.children:
            if isinstance(child, ui.Select) or (isinstance(child, ui.Button) and child.url is None):
                child.disabled = True

        with contextlib.suppress(discord.NotFound, discord.HTTPException):
            await self.message.edit(view=self)


class Modal(ui.Modal):
    def __init__(self, *, title_key: str, lang: str | None) -> None:
        self.lang = lang or DEFAULT_LANG
        super().__init__(title=self.translate(title_key), timeout=600)

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
        return translator.translate(key, lang=self.lang, **kwargs)


class Label[C: ui.Item](ui.Label):
    component: C


class Select[V: BaseView](ui.Select):
    view: V


class Button[V: BaseView](ui.Button):
    view: V


class ChannelSelect[V: BaseView](ui.ChannelSelect):
    view: V


class RoleSelect[V: BaseView](ui.RoleSelect):
    view: V


class TextInput(ui.TextInput):
    pass


class Container(ui.Container):
    pass
