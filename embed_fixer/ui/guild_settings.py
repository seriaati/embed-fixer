from __future__ import annotations

from typing import TYPE_CHECKING

from discord import (
    ButtonStyle,
    ChannelType,
    SelectDefaultValue,
    SelectDefaultValueType,
    SelectOption,
    ui,
)

from ..embed import DefaultEmbed
from ..fixes import FIXES
from ..models import GuildSettings
from .view import View

if TYPE_CHECKING:
    from ..bot import INTERACTION
    from ..translator import Translator


class GuildSettingsView(View):
    async def interaction_check(self, i: INTERACTION) -> bool:
        return i.user.id == self.author.id

    async def start(self, setting: str) -> None:
        await super().start()

        if self.guild is None:
            return
        guild_settings, _ = await GuildSettings.get_or_create(id=self.guild.id)

        if setting == "disable_fixes":
            fix_selector = FixSelector(guild_settings.disabled_fixes)
            fix_selector.placeholder = self.translate("fix_selector_placeholder")
            self.add_item(fix_selector)

        elif setting == "lang":
            lang_selector = LangSelector(self.translator, self.lang)
            lang_selector.placeholder = self.translate("lang_selector_placeholder")
            self.add_item(lang_selector)

        elif setting in {"extract_media_channels", "disable_fix_channels"}:
            if setting == "extract_media_channels":
                extract_media_channel_selector = ExtractMediaChannelSelector(
                    [
                        SelectDefaultValue(id=channel_id, type=SelectDefaultValueType.channel)
                        for channel_id in guild_settings.extract_media_channels
                    ]
                )
                extract_media_channel_selector.placeholder = self.translate(
                    "channel_selector_placeholder"
                )
                self.add_item(extract_media_channel_selector)
            else:
                disable_fix_channel_selector = DisableFixChannelSelector(
                    [
                        SelectDefaultValue(id=channel_id, type=SelectDefaultValueType.channel)
                        for channel_id in guild_settings.disable_fix_channels
                    ]
                )
                disable_fix_channel_selector.placeholder = self.translate(
                    "channel_selector_placeholder"
                )
                self.add_item(disable_fix_channel_selector)

        elif setting == "toggle_webhook_reply":
            webhook_reply_toggle = WebhookReplyToggle(guild_settings.disable_webhook_reply)
            webhook_reply_toggle.label = self.translate(
                "enable_webhook_reply"
                if guild_settings.disable_webhook_reply
                else "disable_webhook_reply"
            )
            self.add_item(webhook_reply_toggle)


class FixSelector(ui.Select[GuildSettingsView]):
    def __init__(self, current: list[str]) -> None:
        super().__init__(
            options=[
                SelectOption(label=domain, value=domain, default=domain in current)
                for domain in FIXES
            ],
            min_values=0,
            max_values=len(FIXES),
        )

    async def callback(self, i: INTERACTION) -> None:
        if i.guild is None or self.view is None:
            return

        guild_settings, _ = await GuildSettings.get_or_create(id=i.guild.id)
        guild_settings.disabled_fixes = self.values
        await guild_settings.save(update_fields=("disabled_fixes",))
        await i.response.send_message(
            embed=DefaultEmbed(title=self.view.translate("settings_saved")), ephemeral=True
        )


class LangSelector(ui.Select[GuildSettingsView]):
    def __init__(self, translator: Translator, current: str) -> None:
        super().__init__(
            options=[
                SelectOption(label=lang_name, value=lang, default=lang == current)
                for lang, lang_name in translator.langs.items()
            ]
        )

    async def callback(self, i: INTERACTION) -> None:
        if i.guild is None or self.view is None:
            return

        guild_settings, _ = await GuildSettings.get_or_create(id=i.guild.id)
        guild_settings.lang = self.values[0]
        await guild_settings.save(update_fields=("lang",))
        await i.response.send_message(
            embed=DefaultEmbed(title=self.view.translate("settings_saved")), ephemeral=True
        )


class ChannelSelect(ui.ChannelSelect):
    def __init__(self, default_values: list[SelectDefaultValue]) -> None:
        super().__init__(
            default_values=default_values,
            max_values=25,
            channel_types=[
                ct
                for ct in ChannelType
                if ct not in {ChannelType.category, ChannelType.group}
            ],
        )


class ExtractMediaChannelSelector(ChannelSelect):
    async def callback(self, i: INTERACTION) -> None:
        if i.guild is None or self.view is None:
            return

        guild_settings, _ = await GuildSettings.get_or_create(id=i.guild.id)
        guild_settings.extract_media_channels = [channel.id for channel in self.values]
        await guild_settings.save(update_fields=("extract_media_channels",))
        await i.response.send_message(
            embed=DefaultEmbed(title=self.view.translate("settings_saved")), ephemeral=True
        )


class DisableFixChannelSelector(ChannelSelect):
    async def callback(self, i: INTERACTION) -> None:
        if i.guild is None or self.view is None:
            return

        guild_settings, _ = await GuildSettings.get_or_create(id=i.guild.id)
        guild_settings.disable_fix_channels = [channel.id for channel in self.values]
        await guild_settings.save(update_fields=("disable_fix_channels",))
        await i.response.send_message(
            embed=DefaultEmbed(title=self.view.translate("settings_saved")), ephemeral=True
        )


class WebhookReplyToggle(ui.Button[GuildSettingsView]):
    def __init__(self, current: bool) -> None:
        super().__init__(style=ButtonStyle.green if current else ButtonStyle.red)
        self.current = current

    def _set_style(self) -> None:
        if self.view is None:
            return
        self.style = ButtonStyle.green if self.current else ButtonStyle.red
        self.label = self.view.translate(
            "enable_webhook_reply" if self.current else "disable_webhook_reply"
        )

    async def callback(self, i: INTERACTION) -> None:
        if i.guild is None or self.view is None:
            return

        guild_settings, _ = await GuildSettings.get_or_create(id=i.guild.id)
        guild_settings.disable_webhook_reply = not guild_settings.disable_webhook_reply
        await guild_settings.save(update_fields=("disable_webhook_reply",))

        self.current = guild_settings.disable_webhook_reply
        self._set_style()
        await i.response.edit_message(view=self.view)
        await i.followup.send(self.view.translate("settings_saved"), ephemeral=True)
