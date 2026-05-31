from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from embed_fixer.core.translator import DEFAULT_LANG
from embed_fixer.settings import UserSetting
from embed_fixer.ui.common import LangSelector, SettingsSection

from . import components as ui

if TYPE_CHECKING:
    from embed_fixer import models


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
                    settings_type="user",
                )
            )

        container.add_item(
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.large)
        )
        container.add_item(
            discord.ui.TextDisplay(f"## {self.translate('lang')}\n{self.translate('lang_desc')}")
        )
        container.add_item(discord.ui.ActionRow(LangSelector(current=lang, settings_type="user")))

        self.add_item(container)
