from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from embed_fixer import models
from embed_fixer.core.translator import DEFAULT_LANG, translator
from embed_fixer.settings import UserSetting

from . import components as ui

if TYPE_CHECKING:
    from embed_fixer.bot import Interaction


class SettingsToggleButton(discord.ui.Button):
    def __init__(
        self, *, value: bool, app_emojis: dict[str, discord.Emoji], settings_key: str
    ) -> None:
        super().__init__(label="...")

        self.app_emojis = app_emojis
        self.value = value
        self.settings_key = settings_key

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
        settings, _ = await models.UserSettings.get_or_create(id=i.user.id)
        self.value = not self.value
        self.update_style()
        setattr(settings, self.settings_key, self.value)
        await settings.save()
        await i.edit_original_response(view=self.view)


class SettingsSection(discord.ui.Section):
    def __init__(
        self,
        *,
        title: str,
        description: str,
        app_emojis: dict[str, discord.Emoji],
        value: bool,
        settings_key: str,
    ) -> None:
        super().__init__(
            discord.ui.TextDisplay(f"## {title}\n{description}"),
            accessory=SettingsToggleButton(
                value=value, app_emojis=app_emojis, settings_key=settings_key
            ),
        )


class UserSettingsView(ui.LayoutView):
    def __init__(
        self,
        *,
        app_emojis: dict[str, discord.Emoji],
        settings: models.UserSettings,
        lang: str | None,
    ) -> None:
        super().__init__(lang=lang)
        lang = settings.lang or DEFAULT_LANG

        container = ui.Container(accent_color=discord.Color.blurple())
        for setting in UserSetting:
            if setting is UserSetting.LANG:
                continue

            container.add_item(
                SettingsSection(
                    title=self.translate(setting.value),
                    description=self.translate(f"{setting.value}_desc"),
                    app_emojis=app_emojis,
                    value=bool(getattr(settings, setting.value)),
                    settings_key=setting.value,
                )
            )

        container.add_item(
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.large)
        )
        container.add_item(
            discord.ui.TextDisplay(f"## {self.translate('lang')}\n{self.translate('lang_desc')}")
        )
        container.add_item(discord.ui.ActionRow(LangSelector(current=lang)))

        self.add_item(container)


class LangSelector(discord.ui.Select):
    def __init__(self, current: str) -> None:
        super().__init__(
            options=[
                discord.SelectOption(label=lang_name, value=lang, default=lang == current)
                for lang, lang_name in translator.langs.items()
            ]
        )

    async def callback(self, i: Interaction) -> None:
        await i.response.defer()
        settings, _ = await models.UserSettings.get_or_create(id=i.user.id)
        settings.lang = self.values[0]
        await settings.save()
