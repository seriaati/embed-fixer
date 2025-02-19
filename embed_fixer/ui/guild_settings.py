from __future__ import annotations

from typing import TYPE_CHECKING

from discord import ButtonStyle, ChannelType, Embed, Guild, SelectOption, ui

from embed_fixer.embed import DefaultEmbed
from embed_fixer.fixes import FIXES
from embed_fixer.models import GuildSettings
from embed_fixer.settings import Setting

from .components import Modal, View

if TYPE_CHECKING:
    from discord.abc import GuildChannel

    from embed_fixer.bot import Interaction
    from embed_fixer.translator import Translator




class GuildSettingsView(View):
    async def interaction_check(self, i: Interaction) -> bool:
        return i.user.id == self.author.id

    async def remove_invalid_channels(self, guild_settings: GuildSettings) -> None:
        guild_channel_ids = [channel.id for channel in self.guild.channels]
        for attr_name in (
            "extract_media_channels",
            "disable_fix_channels",
            "disable_image_spoilers",
        ):
            channel_ids: list[int] = getattr(guild_settings, attr_name)
            valid_channel_ids = [
                channel_id for channel_id in channel_ids if channel_id in guild_channel_ids
            ]
            setattr(guild_settings, attr_name, valid_channel_ids)

        await guild_settings.save()

    def add_selected_channels_field(self, embed: Embed, channel_ids: list[int]) -> Embed:
        channels: list[GuildChannel] = []
        for _, category_channels in self.guild.by_category():
            channels.extend(category_channels)

        channel_ids_: list[int] = []
        for channel in channels:
            if channel.id in channel_ids:
                channel_ids_.append(channel.id)

        embed.clear_fields()
        return embed.add_field(
            name=self.translate("selected_channels"),
            value="\n".join([f"- <#{channel_id}>" for channel_id in channel_ids_]),
        )

    async def start(self, i: Interaction, *, setting: Setting) -> None:
        await super().start()

        embed = DefaultEmbed(
            title=self.translate(setting), description=self.translate(f"{setting}_desc")
        )
        embed.set_footer(text=self.translate("settings_embed_footer"))

        guild_settings, _ = await GuildSettings.get_or_create(id=self.guild.id)
        await self.remove_invalid_channels(guild_settings)

        if setting is Setting.DISABLE_FIXES:
            fix_selector = FixSelector(guild_settings.disabled_fixes)
            fix_selector.placeholder = self.translate("fix_selector_placeholder")
            self.add_item(fix_selector)

        elif setting is Setting.LANG:
            lang_selector = LangSelector(self.translator, self.lang)
            lang_selector.placeholder = self.translate("lang_selector_placeholder")
            self.add_item(lang_selector)

        elif setting is Setting.EXTRACT_MEDIA_CHANNELS:
            selector = ChannelSelect("extract_media_channels")
            selector.placeholder = self.translate("channel_selector_placeholder")
            self.add_item(selector)
            embed = self.add_selected_channels_field(embed, guild_settings.extract_media_channels)

        elif setting is Setting.DISABLE_FIX_CHANNELS:
            selector = ChannelSelect("disable_fix_channels")
            selector.placeholder = self.translate("channel_selector_placeholder")
            self.add_item(selector)
            embed = self.add_selected_channels_field(embed, guild_settings.disable_fix_channels)

        elif setting is Setting.DISABLE_IMAGE_SPOILERS:
            selector = ChannelSelect("disable_image_spoilers")
            selector.placeholder = self.translate("channel_selector_placeholder")
            self.add_item(selector)
            embed = self.add_selected_channels_field(embed, guild_settings.disable_image_spoilers)

        elif setting is Setting.TOGGLE_WEBHOOK_REPLY:
            toggle_btn = WebhookReplyToggle(
                current_toggle=guild_settings.disable_webhook_reply,
                labels={True: "enable_webhook_reply", False: "disable_webhook_reply"},
            )
            toggle_btn.set_style(self)
            self.add_item(toggle_btn)

        elif setting is Setting.TOGGLE_DELETE_REACTION:
            toggle_btn = DisableDeleteReaction(
                current_toggle=guild_settings.disable_delete_reaction,
                labels={True: "enable_delete_reaction", False: "disable_delete_reaction"},
            )
            toggle_btn.set_style(self)
            self.add_item(toggle_btn)

        elif setting is Setting.SHOW_POST_CONTENT_CHANNELS:
            selector = ChannelSelect("show_post_content_channels")
            selector.placeholder = self.translate("channel_selector_placeholder")
            self.add_item(selector)
            embed = self.add_selected_channels_field(
                embed, guild_settings.show_post_content_channels
            )

        elif setting is Setting.USE_VXREDDIT:
            toggle_btn = UseVxreddit(
                current_toggle=guild_settings.use_vxreddit,
                labels={True: "disable_vxreddit", False: "enable_vxreddit"},
            )
            toggle_btn.set_style(self)
            self.add_item(toggle_btn)

        await i.response.send_message(embed=embed, view=self)
        self.message = await i.original_response()


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

    async def callback(self, i: Interaction) -> None:
        if i.guild is None or self.view is None:
            return

        await i.response.defer()
        guild_settings, _ = await GuildSettings.get_or_create(id=i.guild.id)
        guild_settings.disabled_fixes = self.values
        await guild_settings.save(update_fields=("disabled_fixes",))


class LangSelector(ui.Select[GuildSettingsView]):
    def __init__(self, translator: Translator, current: str) -> None:
        super().__init__(
            options=[
                SelectOption(label=lang_name, value=lang, default=lang == current)
                for lang, lang_name in translator.langs.items()
            ]
        )

    async def callback(self, i: Interaction) -> None:
        assert self.view is not None

        await i.response.defer()
        guild_settings, _ = await GuildSettings.get_or_create(id=self.view.guild.id)
        guild_settings.lang = self.values[0]
        await guild_settings.save(update_fields=("lang",))


class ChannelSelect(ui.ChannelSelect[GuildSettingsView]):
    def __init__(self, attr_name: str) -> None:
        super().__init__(
            min_values=0,
            max_values=25,
            channel_types=[
                ct for ct in ChannelType if ct not in {ChannelType.category, ChannelType.group}
            ],
        )
        self.attr_name = attr_name

    async def callback(self, i: Interaction) -> None:
        assert self.view is not None

        guild_settings, _ = await GuildSettings.get_or_create(id=self.view.guild.id)
        channel_ids = [channel.id for channel in self.values]
        current_channel_ids: list[int] = getattr(guild_settings, self.attr_name)

        for channel_id in channel_ids:
            if channel_id in current_channel_ids:
                current_channel_ids.remove(channel_id)
            else:
                current_channel_ids.append(channel_id)

        embed = self.view.message.embeds[0]  # pyright: ignore[reportOptionalMemberAccess]
        embed = self.view.add_selected_channels_field(embed, current_channel_ids)

        await guild_settings.save(update_fields=(self.attr_name,))
        await i.response.edit_message(embed=embed, view=None)
        await i.edit_original_response(view=self.view)


class ToggleButton(ui.Button[GuildSettingsView]):
    def __init__(self, *, current_toggle: bool, labels: dict[bool, str]) -> None:
        super().__init__(style=ButtonStyle.green if current_toggle else ButtonStyle.red)
        self.current_toggle = current_toggle
        self.labels = labels

    def set_style(self, view: View) -> None:
        self.style = ButtonStyle.green if self.current_toggle else ButtonStyle.red
        self.label = view.translate(self.labels[self.current_toggle])


class WebhookReplyToggle(ToggleButton):
    async def callback(self, i: Interaction) -> None:
        assert self.view is not None

        guild_settings, _ = await GuildSettings.get_or_create(id=self.view.guild.id)
        guild_settings.disable_webhook_reply = not guild_settings.disable_webhook_reply
        await guild_settings.save(update_fields=("disable_webhook_reply",))

        self.current_toggle = guild_settings.disable_webhook_reply
        self.set_style(self.view)
        await i.response.edit_message(view=self.view)


class DisableDeleteReaction(ToggleButton):
    async def callback(self, i: Interaction) -> None:
        assert self.view is not None

        guild_settings, _ = await GuildSettings.get_or_create(id=self.view.guild.id)
        guild_settings.disable_delete_reaction = not guild_settings.disable_delete_reaction
        await guild_settings.save(update_fields=("disable_delete_reaction",))

        self.current_toggle = guild_settings.disable_delete_reaction
        self.set_style(self.view)
        await i.response.edit_message(view=self.view)


class UseVxreddit(ToggleButton):
    def set_style(self, view: View) -> None:
        self.style = ButtonStyle.red if self.current_toggle else ButtonStyle.green
        self.label = view.translate(self.labels[self.current_toggle])

    async def callback(self, i: Interaction) -> None:
        assert self.view is not None

        guild_settings, _ = await GuildSettings.get_or_create(id=self.view.guild.id)
        guild_settings.use_vxreddit = not guild_settings.use_vxreddit
        await guild_settings.save(update_fields=("use_vxreddit",))

        self.current_toggle = guild_settings.use_vxreddit
        self.set_style(self.view)
        await i.response.edit_message(view=self.view)
