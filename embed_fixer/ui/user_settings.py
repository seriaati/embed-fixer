from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from embed_fixer.core.translator import DEFAULT_LANG
from embed_fixer.models import ProxyTag, UserSettings
from embed_fixer.settings import UserSetting
from embed_fixer.ui.common import FixModeSelector, LangSelector, SettingsSection

from . import components as ui

if TYPE_CHECKING:
    from embed_fixer import models
    from embed_fixer.bot import Interaction

MAX_PROXY_TAGS = 25


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
            if setting in {UserSetting.LANG, UserSetting.FIX_MODE}:
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
            discord.ui.TextDisplay(
                f"## {self.translate('fix_mode')}\n{self.translate('fix_mode_desc')}"
            )
        )
        container.add_item(
            discord.ui.ActionRow(
                FixModeSelector(current=settings.fix_mode, lang=lang, settings_type="user")
            )
        )

        container.add_item(
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.large)
        )
        container.add_item(
            discord.ui.Section(
                discord.ui.TextDisplay(
                    f"## {self.translate('proxy_tags')}\n{self.translate('proxy_tags_desc')}"
                ),
                accessory=ProxyTagsButton(label=self.translate("edit")),
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


class ProxyTagsButton(ui.Button[UserSettingsView]):
    async def callback(self, i: Interaction) -> None:
        settings, _ = await UserSettings.get_or_create(id=i.user.id)
        await i.response.send_modal(ProxyTagsModal(settings=settings))


class ProxyTagsModal(ui.Modal):
    tags = ui.Label(
        text="proxy_tags",
        component=ui.TextInput(
            style=discord.TextStyle.paragraph, placeholder=":cgg text\n[text]", required=False
        ),
    )

    def __init__(self, *, settings: UserSettings) -> None:
        super().__init__(title_key="proxy_tags", lang=settings.lang)

        self.tags.text = self.translate(self.tags.text)
        self.tags.description = self.translate("proxy_tags_modal_desc")
        self.tags.component.default = "\n".join(tag.to_line() for tag in settings.proxy_tags)

    async def on_submit(self, i: Interaction) -> None:
        lines = [line for line in self.tags.component.value.splitlines() if line.strip()]
        if len(lines) > MAX_PROXY_TAGS:
            await i.response.send_message(
                self.translate("too_many_proxy_tags", max=MAX_PROXY_TAGS), ephemeral=True
            )
            return

        tags: list[ProxyTag] = []
        for line in lines:
            try:
                tags.append(ProxyTag.from_line(line))
            except ValueError:
                await i.response.send_message(
                    self.translate("invalid_proxy_tag", tag=line.strip()), ephemeral=True
                )
                return

        settings, _ = await UserSettings.get_or_create(id=i.user.id)
        settings.proxy_tags = tags
        await settings.save(update_fields=("proxy_tags",))

        await i.response.send_message(self.translate("proxy_tags_saved"), ephemeral=True)
