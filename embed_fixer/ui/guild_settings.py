from __future__ import annotations

import itertools
from typing import TYPE_CHECKING, Literal

import discord
from discord import ButtonStyle, ChannelType, Embed, Guild, SelectOption, Thread, ui

from embed_fixer.embed import DefaultEmbed
from embed_fixer.fixes import DOMAINS, Domain, DomainId
from embed_fixer.models import GuildFixMethod, GuildSettings
from embed_fixer.settings import Setting

from .components import Modal, View

if TYPE_CHECKING:
    from discord.abc import GuildChannel

    from embed_fixer.bot import Interaction
    from embed_fixer.translator import Translator

CHANNEL_IDS_PER_PAGE = 10


class DeleteMsgEmojiModal(Modal):
    emoji = ui.TextInput(label="emoji", max_length=100, placeholder="<:emoji:12345678> / ❌")

    def __init__(self, guild: Guild, translator: Translator, *, settings: GuildSettings) -> None:
        super().__init__(guild, translator, title="delete_msg_emoji")

        self.emoji.label = self.translate(self.emoji.label)
        self.emoji.default = settings.delete_msg_emoji

    async def on_submit(self, i: Interaction) -> None:
        emoji = self.emoji.value

        guild_settings, _ = await GuildSettings.get_or_create(id=self.guild.id)
        guild_settings.delete_msg_emoji = emoji
        await guild_settings.save(update_fields=("delete_msg_emoji",))

        await i.response.send_message(
            content=self.translate("emoji_changed", emoji=emoji), ephemeral=True
        )


class GuildSettingsView(View):
    def __init__(self, guild: discord.Guild, translator: Translator) -> None:
        super().__init__(guild, translator)

        self.domain_id: DomainId | None = None

        self.page = 0
        self.item_ids: list[int] = []
        self.item_type: Literal["channel", "role"] | None = None

    @property
    def domain(self) -> Domain:
        if self.domain_id is None:
            msg = "Domain ID is not set."
            raise ValueError(msg)

        domain = next((domain for domain in DOMAINS if domain.id == self.domain_id), None)
        if domain is None:
            msg = f"Invalid domain ID: {self.domain_id}"
            raise ValueError(msg)

        return domain

    @property
    def page_item_ids(self) -> tuple[int, ...]:
        batched = list(itertools.batched(self.item_ids, CHANNEL_IDS_PER_PAGE))
        if not batched:
            return ()
        self.page = max(min(self.page, len(batched) - 1), 0)
        return batched[self.page]

    async def _update_page(self, i: Interaction) -> None:
        embed = self.message.embeds[0]  # pyright: ignore[reportOptionalMemberAccess]
        if self.item_type == "role":
            embed = self._add_selected_roles_field(embed)
        elif self.item_type == "channel":
            embed = self._add_selected_channels_field(embed)

        await i.response.edit_message(embed=embed, view=None)
        await i.edit_original_response(view=self)

    async def _get_current_fix(self) -> GuildFixMethod | None:
        if self.domain_id is None:
            msg = "Domain ID is not set."
            raise ValueError(msg)

        return await GuildFixMethod.get_or_none(guild_id=self.guild.id, domain_id=self.domain_id)

    async def _get_domain_embed(self) -> DefaultEmbed:
        if self.domain_id is None:
            msg = "Domain ID is not set."
            raise ValueError(msg)

        domain = self.domain
        db_fix = await self._get_current_fix()
        fix = domain.default_fix_method if db_fix is None else domain.get_fix_method(db_fix.fix_id)

        if fix is None:
            fix = domain.default_fix_method
            if fix is None:
                msg = f"Domain {domain.name} has no default fix method."
                raise ValueError(msg)

        service_str = fix.name if fix.repo_url is None else f"[{fix.name}]({fix.repo_url})"
        return DefaultEmbed(
            title=domain.name, description=self.translate("using_fix_service", service=service_str)
        )

    def _get_guild_channel_ids(self) -> list[int]:
        channels: list[GuildChannel | Thread] = []
        for _, category_channels in self.guild.by_category():
            channels.extend(category_channels)
        channels.extend(self.guild.threads)

        return [channel.id for channel in channels]

    async def _remove_invalid_channels(self, guild_settings: GuildSettings) -> None:
        guild_channel_ids = self._get_guild_channel_ids()
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

    def _add_selected_channels_field(self, embed: Embed) -> Embed:
        channel_ids = self.page_item_ids
        if not channel_ids:
            embed.clear_fields()
            return embed

        guild_channel_ids = self._get_guild_channel_ids()
        valid_channel_ids: list[int] = [x for x in guild_channel_ids if x in channel_ids]

        embed.clear_fields()
        return embed.add_field(
            name=self.translate("selected_channels"),
            value="\n".join([f"- <#{channel_id}>" for channel_id in valid_channel_ids]),
        )

    def _add_selected_roles_field(self, embed: Embed) -> Embed:
        role_ids = self.page_item_ids
        if not role_ids:
            embed.clear_fields()
            return embed

        guild_roles = self.guild.roles
        valid_roles = [role for role in guild_roles if role.id in role_ids]

        embed.clear_fields()
        return embed.add_field(
            name=self.translate("selected_roles"),
            value="\n".join([f"- {role.mention}" for role in valid_roles]),
        )

    async def start(self, i: Interaction, *, setting: Setting) -> None:  # noqa: C901, PLR0912, PLR0915
        await i.response.defer(ephemeral=True)
        await super().start()

        embed = DefaultEmbed(
            title=self.translate(setting), description=self.translate(f"{setting}_desc")
        )

        guild_settings, _ = await GuildSettings.get_or_create(id=self.guild.id)
        await self._remove_invalid_channels(guild_settings)

        channel_ids: list[int] | None = None
        role_ids: list[int] | None = None

        if setting is Setting.DISABLE_FIXES:
            fix_selector = FixSelector(guild_settings.disabled_domains)
            fix_selector.placeholder = self.translate("fix_selector_placeholder")
            self.add_item(fix_selector)

        elif setting is Setting.LANG:
            lang_selector = LangSelector(self.translator, self.lang)
            lang_selector.placeholder = self.translate("lang_selector_placeholder")
            self.add_item(lang_selector)

        elif setting is Setting.EXTRACT_MEDIA_CHANNELS:
            selector = ChannelSelect("extract_media_channels", select_type="multiple")
            selector.placeholder = self.translate("channel_selector_placeholder")
            self.add_item(selector)
            channel_ids = guild_settings.extract_media_channels

        elif setting is Setting.DISABLE_FIX_CHANNELS:
            selector = ChannelSelect("disable_fix_channels", select_type="multiple")
            selector.placeholder = self.translate("channel_selector_placeholder")
            self.add_item(selector)
            channel_ids = guild_settings.disable_fix_channels

        elif setting is Setting.ENABLE_FIX_CHANNELS:
            selector = ChannelSelect("enable_fix_channels", select_type="multiple")
            selector.placeholder = self.translate("channel_selector_placeholder")
            self.add_item(selector)
            channel_ids = guild_settings.enable_fix_channels

        elif setting is Setting.DISABLE_IMAGE_SPOILERS:
            selector = ChannelSelect("disable_image_spoilers", select_type="multiple")
            selector.placeholder = self.translate("channel_selector_placeholder")
            self.add_item(selector)
            channel_ids = guild_settings.disable_image_spoilers

        elif setting is Setting.TOGGLE_WEBHOOK_REPLY:
            toggle_btn = ToggleButton(
                current_toggle=guild_settings.disable_webhook_reply,
                labels={True: "enable_webhook_reply", False: "disable_webhook_reply"},
                attr_name="disable_webhook_reply",
                reverse_color=False,
            )
            toggle_btn.set_style(self)
            self.add_item(toggle_btn)

        elif setting is Setting.TOGGLE_DELETE_REACTION:
            toggle_btn = ToggleButton(
                current_toggle=guild_settings.disable_delete_reaction,
                labels={True: "enable_delete_reaction", False: "disable_delete_reaction"},
                attr_name="disable_delete_reaction",
                reverse_color=False,
            )
            toggle_btn.set_style(self)
            self.add_item(toggle_btn)

        elif setting is Setting.BOT_VISIBILITY:
            toggle_btn = ToggleButton(
                current_toggle=guild_settings.bot_visibility,
                labels={True: "disable_bot_visibility", False: "enable_bot_visibility"},
                attr_name="bot_visibility",
                reverse_color=True,
            )
            toggle_btn.set_style(self)
            self.add_item(toggle_btn)

        elif setting is Setting.SHOW_POST_CONTENT_CHANNELS:
            selector = ChannelSelect("show_post_content_channels", select_type="multiple")
            selector.placeholder = self.translate("channel_selector_placeholder")
            self.add_item(selector)
            channel_ids = guild_settings.show_post_content_channels

        elif setting is Setting.CHOOSE_FIX_SERVICE:
            self.domain_id = DOMAINS[0].id
            embed = await self._get_domain_embed()

            domain_selector = DomainSelector(self.domain_id or DomainId.TWITTER)
            self.add_item(domain_selector)

            current = await self._get_current_fix()
            fix_method_selector = FixMethodSelector(
                self.domain, None if current is None else current.fix_id
            )
            self.add_item(fix_method_selector)

        elif setting is Setting.FUNNEL_TARGET_CHANNEL:
            channel_selector = ChannelSelect("funnel_target_channel", select_type="single")
            channel_selector.placeholder = self.translate("channel_selector_placeholder")
            self.add_item(channel_selector)
            if guild_settings.funnel_target_channel is not None:
                channel_ids = [guild_settings.funnel_target_channel]

        elif setting is Setting.WHITELIST_ROLE_IDS:
            role_selector = RoleSelect("whitelist_role_ids")
            role_selector.placeholder = self.translate("role_selector_placeholder")
            self.add_item(role_selector)
            role_ids = guild_settings.whitelist_role_ids

        else:
            msg = f"Unknown setting: {setting!r}"
            raise ValueError(msg)

        if channel_ids is not None:
            self.item_ids = channel_ids
            embed = self._add_selected_channels_field(embed)
        elif role_ids is not None:
            self.item_ids = role_ids
            embed = self._add_selected_roles_field(embed)

        if channel_ids is not None or role_ids is not None:
            self.add_item(PreviousButton(label=self.translate("previous")))
            self.add_item(NextButton(label=self.translate("next")))

        await i.followup.send(
            content=self.translate("settings_embed_footer"), embed=embed, view=self
        )
        self.message = await i.original_response()


class FixSelector(ui.Select[GuildSettingsView]):
    def __init__(self, current: list[int]) -> None:
        super().__init__(
            options=[
                SelectOption(
                    label=domain.name,
                    value=str(domain.id.value),
                    default=domain.id.value in current,
                )
                for domain in DOMAINS
            ],
            min_values=0,
            max_values=len(DOMAINS),
        )

    async def callback(self, i: Interaction) -> None:
        if i.guild is None or self.view is None:
            return

        await i.response.defer()
        guild_settings, _ = await GuildSettings.get_or_create(id=i.guild.id)
        guild_settings.disabled_domains = [int(domain) for domain in self.values]
        await guild_settings.save(update_fields=("disabled_domains",))


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
    def __init__(self, attr_name: str, *, select_type: Literal["single", "multiple"]) -> None:
        super().__init__(
            min_values=0,
            max_values=25 if select_type == "multiple" else 1,
            channel_types=[
                ct
                for ct in ChannelType
                if ct not in {ChannelType.category, ChannelType.group, ChannelType.forum}
            ],
        )

        self.attr_name = attr_name
        self.select_type = select_type

    async def callback(self, i: Interaction) -> None:
        assert self.view is not None

        guild_settings, _ = await GuildSettings.get_or_create(id=self.view.guild.id)
        channel_ids = [channel.id for channel in self.values]

        current_channel_ids: list[int | None]

        if self.select_type == "multiple":
            current_channel_ids = getattr(guild_settings, self.attr_name, [])
        else:
            current_channel_ids = [getattr(guild_settings, self.attr_name)]

        current_channel_ids = [x for x in current_channel_ids if x is not None]

        for channel_id in channel_ids:
            if channel_id in current_channel_ids:
                current_channel_ids.remove(channel_id)
            else:
                current_channel_ids.append(channel_id)

        self.view.page = 0
        self.view.item_ids = current_channel_ids  # pyright: ignore[reportAttributeAccessIssue]

        if self.select_type == "multiple":
            setattr(guild_settings, self.attr_name, current_channel_ids)
        else:
            setattr(
                guild_settings,
                self.attr_name,
                current_channel_ids[0] if current_channel_ids else None,
            )

        await guild_settings.save(update_fields=(self.attr_name,))

        embed = self.view.message.embeds[0]  # pyright: ignore[reportOptionalMemberAccess]
        embed = self.view._add_selected_channels_field(embed)
        await i.response.edit_message(embed=embed, view=None)
        await i.edit_original_response(view=self.view)


class RoleSelect(ui.RoleSelect[GuildSettingsView]):
    def __init__(self, attr_name: str) -> None:
        super().__init__(min_values=0, max_values=25)
        self.attr_name = attr_name

    async def callback(self, i: Interaction) -> None:
        assert self.view is not None

        guild_settings, _ = await GuildSettings.get_or_create(id=self.view.guild.id)
        role_ids = [role.id for role in self.values]

        current_role_ids: list[int] = getattr(guild_settings, self.attr_name, [])

        for role_id in role_ids:
            if role_id in current_role_ids:
                current_role_ids.remove(role_id)
            else:
                current_role_ids.append(role_id)

        self.view.page = 0
        self.view.item_ids = current_role_ids

        setattr(guild_settings, self.attr_name, current_role_ids)
        await guild_settings.save(update_fields=(self.attr_name,))

        embed = self.view.message.embeds[0]  # pyright: ignore[reportOptionalMemberAccess]
        embed = self.view._add_selected_roles_field(embed)
        await i.response.edit_message(embed=embed, view=None)
        await i.edit_original_response(view=self.view)


class ToggleButton(ui.Button[GuildSettingsView]):
    def __init__(
        self, *, current_toggle: bool, labels: dict[bool, str], attr_name: str, reverse_color: bool
    ) -> None:
        self.current_toggle = current_toggle
        self.labels = labels
        self.attr_name = attr_name
        self.reverse_color = reverse_color
        super().__init__()

    def set_style(self, view: View) -> None:
        if self.reverse_color:
            self.style = ButtonStyle.red if self.current_toggle else ButtonStyle.green
        else:
            self.style = ButtonStyle.green if self.current_toggle else ButtonStyle.red
        self.label = view.translate(self.labels[self.current_toggle])

    async def callback(self, i: Interaction) -> None:
        if self.view is None:
            return

        await i.response.defer()
        guild_settings, _ = await GuildSettings.get_or_create(id=self.view.guild.id)
        setattr(guild_settings, self.attr_name, not self.current_toggle)
        await guild_settings.save(update_fields=(self.attr_name,))

        self.current_toggle = not self.current_toggle
        self.set_style(self.view)
        await i.edit_original_response(view=self.view)


class DomainSelector(ui.Select[GuildSettingsView]):
    def __init__(self, domain_id: DomainId) -> None:
        super().__init__(
            options=[
                SelectOption(
                    label=domain.name, value=str(domain.id.value), default=domain.id == domain_id
                )
                for domain in DOMAINS
                if domain.fix_methods
            ]
        )

    async def callback(self, i: Interaction) -> None:
        if self.view is None:
            return

        self.view.domain_id = DomainId(int(self.values[0]))
        embed = await self.view._get_domain_embed()

        self.options = [
            SelectOption(
                label=domain.name,
                value=str(domain.id.value),
                default=domain.id == self.view.domain_id,
            )
            for domain in DOMAINS
            if domain.fix_methods
        ]

        current = await self.view._get_current_fix()
        fix_method_selector = FixMethodSelector(
            self.view.domain, None if current is None else current.fix_id
        )
        current_selector = self.view.get_item("guild_settings:fix_method_selector")
        if current_selector is not None:
            self.view.remove_item(current_selector)

        self.view.add_item(fix_method_selector)
        await i.response.edit_message(embed=embed, view=self.view)


class FixMethodSelector(ui.Select[GuildSettingsView]):
    def __init__(self, domain: Domain, current: int | None) -> None:
        super().__init__(
            options=[
                SelectOption(
                    label=method.name,
                    value=str(method.id),
                    default=method.default if current is None else method.id == current,
                )
                for method in domain.fix_methods
            ],
            custom_id="guild_settings:fix_method_selector",
        )

    async def callback(self, i: Interaction) -> None:
        if self.view is None:
            return

        await i.response.defer()

        current = await self.view._get_current_fix()
        if current is None:
            await GuildFixMethod.create(
                guild_id=self.view.guild.id,
                domain_id=self.view.domain_id,
                fix_id=int(self.values[0]),
            )
        else:
            current.fix_id = int(self.values[0])
            await current.save(update_fields=("fix_id",))

        embed = await self.view._get_domain_embed()
        for option in self.options:
            option.default = option.value == self.values[0]

        await i.edit_original_response(embed=embed, view=self.view)


class NextButton(ui.Button[GuildSettingsView]):
    def __init__(self, *, label: str) -> None:
        super().__init__(label=label, style=ButtonStyle.primary)

    async def callback(self, i: Interaction) -> None:
        assert self.view is not None
        self.view.page += 1
        await self.view._update_page(i)


class PreviousButton(ui.Button[GuildSettingsView]):
    def __init__(self, *, label: str) -> None:
        super().__init__(label=label, style=ButtonStyle.primary)

    async def callback(self, i: Interaction) -> None:
        assert self.view is not None
        self.view.page -= 1
        await self.view._update_page(i)
