from __future__ import annotations

import itertools
from typing import TYPE_CHECKING, Any, Literal, cast

import discord
from discord import ButtonStyle, ChannelType, SelectOption

from embed_fixer.core.translator import DEFAULT_LANG, translator
from embed_fixer.fixes import DOMAINS, DomainId
from embed_fixer.models import GuildFixMethod, GuildSettings
from embed_fixer.settings import GuildSetting
from embed_fixer.ui.common import SettingsSection

from . import components as ui

if TYPE_CHECKING:
    from discord import Thread
    from discord.abc import GuildChannel

    from embed_fixer.bot import Interaction
    from embed_fixer.fixes import Domain

ITEM_IDS_PER_PAGE = 10  # Channel/Role IDs to show per page

SELECTED_ITEMS_TEXT_ID = 1
FIX_METHOD_SELECTOR_ROW_ID = 2
DOMAIN_TEXT_DISPLAY_ID = 3
PAGINATOR_ACTION_ROW_ID = 4
DOMAIN_SELECTOR_ROW_ID = 5
FIX_SELECTOR_ROW_ID = 6
LANG_SELECTOR_ROW_ID = 7
CHANNEL_SELECTOR_ROW_ID = 8
ROLE_SELECTOR_ROW_ID = 9

NO_HEADER_SETTINGS = {
    GuildSetting.TOGGLE_WEBHOOK_REPLY,
    GuildSetting.TOGGLE_DELETE_REACTION,
    GuildSetting.BOT_VISIBILITY,
    GuildSetting.SHOW_ORIGINAL_LINK_BUTTON,
    GuildSetting.DELETE_ORIGINAL_MESSAGE_IN_THREADS,
    GuildSetting.REPLY_INSTEAD_OF_DELETE,
}

MULTI_CHANNEL_SETTING_ATTRS: dict[GuildSetting, str] = {
    GuildSetting.EXTRACT_MEDIA_CHANNELS: "extract_media_channels",
    GuildSetting.DISABLE_FIX_CHANNELS: "disable_fix_channels",
    GuildSetting.ENABLE_FIX_CHANNELS: "enable_fix_channels",
    GuildSetting.DISABLE_IMAGE_SPOILERS: "disable_image_spoilers",
    GuildSetting.SHOW_POST_CONTENT_CHANNELS: "show_post_content_channels",
}

SINGLE_CHANNEL_SETTING_ATTRS: dict[GuildSetting, str] = {
    GuildSetting.FUNNEL_TARGET_CHANNEL: "funnel_target_channel"
}

ROLE_SETTING_ATTRS: dict[GuildSetting, str] = {
    GuildSetting.WHITELIST_ROLE_IDS: "whitelist_role_ids"
}

TOGGLE_SETTING_ATTRS: dict[GuildSetting, str] = {
    GuildSetting.TOGGLE_WEBHOOK_REPLY: "disable_webhook_reply",
    GuildSetting.TOGGLE_DELETE_REACTION: "disable_delete_reaction",
    GuildSetting.BOT_VISIBILITY: "bot_visibility",
    GuildSetting.SHOW_ORIGINAL_LINK_BUTTON: "show_original_link_btn",
    GuildSetting.DELETE_ORIGINAL_MESSAGE_IN_THREADS: "delete_original_message_in_threads",
    GuildSetting.REPLY_INSTEAD_OF_DELETE: "reply_instead_of_delete",
}


class DeleteMsgEmojiModal(ui.Modal):
    emoji = ui.Label(
        text="emoji", component=ui.TextInput(max_length=100, placeholder="<:emoji:12345678> / ❌")
    )

    def __init__(self, *, settings: GuildSettings) -> None:
        self.lang = lang = settings.lang or DEFAULT_LANG
        super().__init__(title_key="delete_msg_emoji", lang=settings.lang)

        self.emoji.text = translator.translate(self.emoji.text, lang=lang)
        self.emoji.component.default = settings.delete_msg_emoji
        self.settings = settings

    async def on_submit(self, i: Interaction) -> None:
        emoji = self.emoji.component.value

        guild_settings, _ = await GuildSettings.get_or_create(id=self.settings.id)
        guild_settings.delete_msg_emoji = emoji
        await guild_settings.save(update_fields=("delete_msg_emoji",))

        await i.response.send_message(
            content=translator.translate("emoji_changed", lang=self.lang, emoji=emoji),
            ephemeral=True,
        )


MIN_SECONDS = 1
MAX_SECONDS = 3600  # 1 hour


class RemoveDeleteReactionAfterModal(ui.Modal):
    seconds = ui.Label(
        text="seconds", component=ui.TextInput(max_length=19, placeholder="...", required=False)
    )

    def __init__(self, *, settings: GuildSettings) -> None:
        self.lang = lang = settings.lang or DEFAULT_LANG
        super().__init__(title_key="remove_delete_reaction_after", lang=settings.lang)

        self.seconds.text = translator.translate("seconds", lang=lang)
        self.seconds.component.placeholder = translator.translate(
            "seconds_placeholder", lang=lang, min=MIN_SECONDS, max=MAX_SECONDS
        )
        self.seconds.component.default = (
            str(settings.remove_delete_reaction_after)
            if settings.remove_delete_reaction_after is not None
            else None
        )
        self.settings = settings

    async def on_submit(self, i: Interaction) -> None:
        raw = self.seconds.component.value.strip()

        guild_settings, _ = await GuildSettings.get_or_create(id=self.settings.id)

        if not raw:
            guild_settings.remove_delete_reaction_after = None
            await guild_settings.save(update_fields=("remove_delete_reaction_after",))
            await i.response.send_message(
                content=translator.translate(
                    "remove_delete_reaction_after_disabled", lang=self.lang
                ),
                ephemeral=True,
            )
            return

        try:
            seconds = int(raw)
        except ValueError:
            await i.response.send_message(
                content=translator.translate(
                    "invalid_seconds", lang=self.lang, min=MIN_SECONDS, max=MAX_SECONDS
                ),
                ephemeral=True,
            )
            return

        if seconds < MIN_SECONDS or seconds > MAX_SECONDS:
            await i.response.send_message(
                content=translator.translate(
                    "invalid_seconds", lang=self.lang, min=MIN_SECONDS, max=MAX_SECONDS
                ),
                ephemeral=True,
            )
            return

        guild_settings.remove_delete_reaction_after = seconds
        await guild_settings.save(update_fields=("remove_delete_reaction_after",))

        await i.response.send_message(
            content=translator.translate(
                "remove_delete_reaction_after_changed", lang=self.lang, seconds=seconds
            ),
            ephemeral=True,
        )


class GuildSettingsView(ui.LayoutView):
    def __init__(
        self, *, guild: discord.Guild, lang: str | None, app_emojis: dict[str, discord.Emoji]
    ) -> None:
        super().__init__(lang=lang)

        self.domain_id: DomainId | None = None
        self.guild = guild
        self.guild_id = guild.id
        self.app_emojis = app_emojis

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
        batched = list(itertools.batched(self.item_ids, ITEM_IDS_PER_PAGE))
        if not batched:
            return ()
        self.page = max(min(self.page, len(batched) - 1), 0)
        return batched[self.page]

    def _add_selector_action_row(
        self,
        container: ui.Container,
        selector: discord.ui.Item[Any],
        *,
        action_row_id: int | None = None,
    ) -> None:
        container.add_item(discord.ui.ActionRow(selector, id=action_row_id))

    async def _hard_rerender(self, i: Interaction) -> None:
        view = ui.LayoutView(lang=None)
        view.add_item(
            ui.Container(discord.ui.TextDisplay("..."), accent_color=discord.Color.blurple())
        )

        if i.response.is_done():
            await i.edit_original_response(view=view)
        else:
            await i.response.edit_message(view=view)

        await i.edit_original_response(view=self)

    async def _update_page(self, i: Interaction) -> None:
        container = self.children[0]
        container = cast("ui.Container", container)

        if self.item_type == "role":
            container = self._add_selected_roles_field(container)
        elif self.item_type == "channel":
            container = self._add_selected_channels_field(container)

        await i.response.edit_message(view=self)

    async def _get_current_fix(self) -> GuildFixMethod | None:
        if self.domain_id is None:
            msg = "Domain ID is not set."
            raise ValueError(msg)

        return await GuildFixMethod.get_or_none(guild_id=self.guild_id, domain_id=self.domain_id)

    async def _get_domain_text_display(self) -> discord.ui.TextDisplay:
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
        return discord.ui.TextDisplay(
            f"## {domain.name}\n{self.translate('using_fix_service', service=service_str)}",
            id=DOMAIN_TEXT_DISPLAY_ID,
        )

    def _get_guild_channel_ids(self) -> list[int]:
        channels: list[GuildChannel | Thread] = []
        for _, category_channels in self.guild.by_category():
            channels.extend(category_channels)
        channels.extend(self.guild.threads)

        return [channel.id for channel in channels]

    async def _remove_invalid_channels(self, guild_settings: GuildSettings) -> None:
        guild_channel_ids = self._get_guild_channel_ids()
        updated_fields: list[str] = []

        for attr_name in (
            "extract_media_channels",
            "disable_fix_channels",
            "disable_image_spoilers",
        ):
            channel_ids: list[int] = getattr(guild_settings, attr_name)
            valid_channel_ids = [
                channel_id for channel_id in channel_ids if channel_id in guild_channel_ids
            ]
            if valid_channel_ids != channel_ids:
                setattr(guild_settings, attr_name, valid_channel_ids)
                updated_fields.append(attr_name)

        if updated_fields:
            await guild_settings.save()

    def _add_selected_items_field(
        self, container: ui.Container, *, title_key: str, lines: list[str]
    ) -> ui.Container:
        self.remove_child_by_id(
            container, item_type=discord.ui.TextDisplay, item_id=SELECTED_ITEMS_TEXT_ID
        )
        paginator_action_row = self.remove_child_by_id(
            container, item_type=discord.ui.ActionRow, item_id=PAGINATOR_ACTION_ROW_ID
        )

        container.add_item(
            discord.ui.TextDisplay(
                f"## {self.translate(title_key)}\n{'\n'.join(lines)}", id=SELECTED_ITEMS_TEXT_ID
            )
        )
        if paginator_action_row is not None:
            container.add_item(paginator_action_row)

        return container

    def _add_selected_channels_field(self, container: ui.Container) -> ui.Container:
        channel_ids = self.page_item_ids
        guild_channel_ids = self._get_guild_channel_ids()
        valid_channel_ids: list[int] = [x for x in guild_channel_ids if x in channel_ids]
        lines = [f"- <#{channel_id}>" for channel_id in valid_channel_ids]
        return self._add_selected_items_field(container, title_key="selected_channels", lines=lines)

    def _add_selected_roles_field(self, container: ui.Container) -> ui.Container:
        role_ids = self.page_item_ids
        guild_roles = self.guild.roles
        valid_roles = [role for role in guild_roles if role.id in role_ids]
        lines = [f"- {role.mention}" for role in valid_roles]
        return self._add_selected_items_field(container, title_key="selected_roles", lines=lines)

    def _add_toggle_section(
        self,
        container: ui.Container,
        *,
        setting: GuildSetting,
        guild_settings: GuildSettings,
        settings_attr: str,
    ) -> None:
        section = SettingsSection(
            title=self.translate(setting.value),
            description=self.translate(f"{setting.value}_desc"),
            app_emojis=self.app_emojis,
            value=cast("bool", getattr(guild_settings, settings_attr)),
            settings_key=settings_attr,
            settings_type="guild",
        )
        container.add_item(section)

    def _add_multi_channel_selector_for_setting(
        self, container: ui.Container, *, guild_settings: GuildSettings, attr_name: str
    ) -> list[int]:
        selector = ChannelSelect(attr_name, select_type="multiple")
        self._add_selector_action_row(container, selector, action_row_id=CHANNEL_SELECTOR_ROW_ID)
        return cast("list[int]", getattr(guild_settings, attr_name))

    def _add_single_channel_selector_for_setting(
        self, container: ui.Container, *, attr_name: str
    ) -> None:
        selector = ChannelSelect(attr_name, select_type="single")
        self._add_selector_action_row(container, selector, action_row_id=CHANNEL_SELECTOR_ROW_ID)

    def _add_role_selector_for_setting(
        self, container: ui.Container, *, guild_settings: GuildSettings, attr_name: str
    ) -> list[int]:
        selector = RoleSelect(attr_name)
        self._add_selector_action_row(container, selector, action_row_id=ROLE_SELECTOR_ROW_ID)
        return cast("list[int]", getattr(guild_settings, attr_name))

    async def start(self, i: Interaction, *, setting: GuildSetting) -> None:
        await i.response.defer(ephemeral=True)

        guild_settings, _ = await GuildSettings.get_or_create(id=self.guild.id)
        await self._remove_invalid_channels(guild_settings)

        channel_ids: list[int] | None = None
        role_ids: list[int] | None = None

        container = ui.Container(accent_color=discord.Color.blurple())

        if setting not in NO_HEADER_SETTINGS:
            container.add_item(
                discord.ui.TextDisplay(
                    f"# {self.translate(setting)}\n{self.translate(f'{setting}_desc')}"
                )
            )

        if setting is GuildSetting.DISABLE_FIXES:
            fix_selector = DisableDomainSelect(guild_settings.disabled_domains)
            self._add_selector_action_row(
                container, fix_selector, action_row_id=FIX_SELECTOR_ROW_ID
            )

        elif setting is GuildSetting.LANG:
            lang_selector = LangSelector(current=self.lang or DEFAULT_LANG)
            self._add_selector_action_row(
                container, lang_selector, action_row_id=LANG_SELECTOR_ROW_ID
            )

        elif setting in MULTI_CHANNEL_SETTING_ATTRS:
            channel_ids = self._add_multi_channel_selector_for_setting(
                container,
                guild_settings=guild_settings,
                attr_name=MULTI_CHANNEL_SETTING_ATTRS[setting],
            )

        elif setting in TOGGLE_SETTING_ATTRS:
            self._add_toggle_section(
                container,
                setting=setting,
                guild_settings=guild_settings,
                settings_attr=TOGGLE_SETTING_ATTRS[setting],
            )

        elif setting is GuildSetting.CHOOSE_FIX_SERVICE:
            self.domain_id = DOMAINS[0].id
            text_display = await self._get_domain_text_display()
            container.add_item(text_display)

            domain_selector = DomainSelector(self.domain_id or DomainId.TWITTER)
            container.add_item(discord.ui.ActionRow(domain_selector, id=DOMAIN_SELECTOR_ROW_ID))

            current = await self._get_current_fix()
            fix_method_selector = FixMethodSelector(
                self.domain, None if current is None else current.fix_id
            )
            container.add_item(
                discord.ui.ActionRow(fix_method_selector, id=FIX_METHOD_SELECTOR_ROW_ID)
            )

        elif setting in SINGLE_CHANNEL_SETTING_ATTRS:
            self._add_single_channel_selector_for_setting(
                container, attr_name=SINGLE_CHANNEL_SETTING_ATTRS[setting]
            )

        elif setting in ROLE_SETTING_ATTRS:
            role_ids = self._add_role_selector_for_setting(
                container, guild_settings=guild_settings, attr_name=ROLE_SETTING_ATTRS[setting]
            )

        else:
            msg = f"Unknown setting: {setting!r}"
            raise ValueError(msg)

        if channel_ids is not None or role_ids is not None:
            container.add_item(
                discord.ui.ActionRow(
                    PreviousButton(emoji=self.app_emojis["ARROW_BACK"]),
                    NextButton(emoji=self.app_emojis["ARROW_FORWARD"]),
                    id=PAGINATOR_ACTION_ROW_ID,
                )
            )

        if channel_ids is not None:
            self.item_ids = channel_ids
            self.item_type = "channel"
            container = self._add_selected_channels_field(container)
        elif role_ids is not None:
            self.item_ids = role_ids
            self.item_type = "role"
            container = self._add_selected_roles_field(container)

        self.add_item(container)
        await i.followup.send(view=self, ephemeral=True)
        self.message = await i.original_response()


class DisableDomainSelect(ui.Select[GuildSettingsView]):
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
        if i.guild is None:
            return

        await i.response.defer()

        guild_settings, _ = await GuildSettings.get_or_create(id=i.guild.id)
        guild_settings.disabled_domains = [int(domain) for domain in self.values]
        await guild_settings.save(update_fields=("disabled_domains",))


class LangSelector(ui.Select[GuildSettingsView]):
    def __init__(self, *, current: str) -> None:
        super().__init__(
            options=[
                SelectOption(label=lang_name, value=lang, default=lang == current)
                for lang, lang_name in translator.langs.items()
            ]
        )

    async def callback(self, i: Interaction) -> None:
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
        self.select_type: Literal["single", "multiple"] = select_type

    async def callback(self, i: Interaction) -> None:
        await i.response.defer()

        guild_settings, _ = await GuildSettings.get_or_create(id=self.view.guild.id)

        if self.select_type == "multiple":
            current_channel_ids = getattr(guild_settings, self.attr_name, [])
            for channel_id in [channel.id for channel in self.values]:
                if channel_id in current_channel_ids:
                    current_channel_ids.remove(channel_id)
                else:
                    current_channel_ids.append(channel_id)

            setattr(guild_settings, self.attr_name, current_channel_ids)

            self.view.page = 0
            self.view.item_ids = current_channel_ids
        else:
            setattr(guild_settings, self.attr_name, self.values[0].id if self.values else None)

        await guild_settings.save(update_fields=(self.attr_name,))

        if self.select_type == "multiple":
            container = self.view.children[0]
            container = cast("ui.Container", container)
            container = self.view._add_selected_channels_field(container)

            await self.view._hard_rerender(i)
        else:
            channel_id: int | None = getattr(guild_settings, self.attr_name)
            if channel_id is None:
                self.default_values = []
            else:
                self.default_values = (
                    [
                        discord.SelectDefaultValue(
                            id=channel_id, type=discord.SelectDefaultValueType.channel
                        )
                    ]
                    if channel_id
                    else []
                )
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

        container = self.view.children[0]
        container = cast("ui.Container", container)
        container = self.view._add_selected_roles_field(container)

        await self.view._hard_rerender(i)


class DomainSelector(ui.Select[GuildSettingsView]):
    def __init__(self, domain_id: DomainId) -> None:
        super().__init__(options=self._get_options(domain_id))

    @staticmethod
    def _get_options(domain_id: DomainId) -> list[SelectOption]:
        return [
            SelectOption(
                label=domain.name, value=str(domain.id.value), default=domain.id == domain_id
            )
            for domain in DOMAINS
            if domain.fix_methods
        ]

    async def callback(self, i: Interaction) -> None:
        self.view.domain_id = DomainId(int(self.values[0]))
        self.options = self._get_options(self.view.domain_id)

        current = await self.view._get_current_fix()
        fix_method_selector = FixMethodSelector(
            self.view.domain, None if current is None else current.fix_id
        )

        container = self.view.children[0]
        container = cast("ui.Container", container)
        self.view.replace_child_by_id(
            container,
            item_type=discord.ui.TextDisplay,
            item_id=DOMAIN_TEXT_DISPLAY_ID,
            new_child=await self.view._get_domain_text_display(),
        )
        self.view.replace_child_by_id(
            container,
            item_type=discord.ui.ActionRow,
            item_id=FIX_METHOD_SELECTOR_ROW_ID,
            new_child=discord.ui.ActionRow(fix_method_selector, id=FIX_METHOD_SELECTOR_ROW_ID),
        )

        await i.response.edit_message(view=self.view)


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
        await GuildFixMethod.update_or_create(
            guild_id=self.view.guild.id,
            domain_id=self.view.domain_id,
            defaults={"fix_id": int(self.values[0])},
        )

        text_display = await self.view._get_domain_text_display()

        container = self.view.children[0]
        container = cast("ui.Container", container)

        self.view.replace_child_by_id(
            container,
            item_type=discord.ui.TextDisplay,
            item_id=DOMAIN_TEXT_DISPLAY_ID,
            new_child=text_display,
        )

        await i.response.edit_message(view=self.view)


class NextButton(ui.Button[GuildSettingsView]):
    def __init__(self, *, emoji: discord.Emoji) -> None:
        super().__init__(emoji=emoji, style=ButtonStyle.primary)

    async def callback(self, i: Interaction) -> None:
        assert self.view is not None
        self.view.page += 1
        await self.view._update_page(i)


class PreviousButton(ui.Button[GuildSettingsView]):
    def __init__(self, *, emoji: discord.Emoji) -> None:
        super().__init__(emoji=emoji, style=ButtonStyle.primary)

    async def callback(self, i: Interaction) -> None:
        assert self.view is not None
        self.view.page -= 1
        await self.view._update_page(i)
