from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import discord

from embed_fixer.core.translator import translator
from embed_fixer.models import GuildSettings, UserSettings

from . import components as ui

if TYPE_CHECKING:
    from embed_fixer.bot import Interaction


class LangSelector(ui.Select):
    def __init__(self, current: str, *, settings_type: Literal["guild", "user"]) -> None:
        super().__init__(
            options=[
                discord.SelectOption(label=lang_name, value=lang, default=lang == current)
                for lang, lang_name in translator.langs.items()
            ]
        )
        self.settings_type = settings_type

    async def callback(self, i: Interaction) -> None:
        await i.response.defer()
        settings_cls = GuildSettings if self.settings_type == "guild" else UserSettings
        settings, _ = await settings_cls.get_or_create(id=i.user.id)
        settings.lang = self.values[0]
        await settings.save()


class SettingsToggleButton(discord.ui.Button):
    def __init__(
        self,
        *,
        value: bool,
        app_emojis: dict[str, discord.Emoji],
        settings_key: str,
        settings_type: Literal["guild", "user"],
    ) -> None:
        super().__init__(label="...")

        self.app_emojis = app_emojis
        self.value = value
        self.settings_key = settings_key
        self.settings_type = settings_type

        self.update_style()

    def update_style(self) -> None:
        self.style = discord.ButtonStyle.green if self.value else discord.ButtonStyle.gray
        emoji = self.app_emojis.get("TOGGLE_ON" if self.value else "TOGGLE_OFF")
        if emoji:
            self.label = None
            self.emoji = emoji
        else:
            self.label = "ON" if self.value else "OFF"

    async def callback(self, i: Interaction) -> None:
        await i.response.defer()
        settings_cls = GuildSettings if self.settings_type == "guild" else UserSettings
        settings, _ = await settings_cls.get_or_create(id=i.user.id)
        self.value = not self.value
        self.update_style()
        setattr(settings, self.settings_key, self.value)
        await settings.save()
        await i.edit_original_response(view=self.view)


class SettingsSection(discord.ui.Section):
    def __init__(  # noqa: PLR0913
        self,
        *,
        title: str,
        description: str,
        app_emojis: dict[str, discord.Emoji],
        value: bool,
        settings_key: str,
        settings_type: Literal["guild", "user"],
    ) -> None:
        super().__init__(
            discord.ui.TextDisplay(f"## {title}\n{description}"),
            accessory=SettingsToggleButton(
                value=value,
                app_emojis=app_emojis,
                settings_key=settings_key,
                settings_type=settings_type,
            ),
        )
