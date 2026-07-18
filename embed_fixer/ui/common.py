from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, cast

import discord

from embed_fixer.core.translator import translator
from embed_fixer.models import GuildSettings, UserSettings
from embed_fixer.settings import FixMode

from . import components as ui

if TYPE_CHECKING:
    from embed_fixer.bot import Interaction

FOLLOW_GUILD_VALUE = "follow_guild"


class LangSelector(ui.Select):
    def __init__(self, current: str, *, settings_type: Literal["guild", "user"]) -> None:
        super().__init__(
            options=[
                discord.SelectOption(label=lang_name, value=lang, default=lang == current)
                for lang, lang_name in translator.langs.items()
            ]
        )
        self.settings_type: Literal["guild", "user"] = settings_type

    async def callback(self, i: Interaction) -> None:
        settings_cls = GuildSettings if self.settings_type == "guild" else UserSettings
        settings, _ = await settings_cls.get_or_create(id=i.user.id)
        settings.lang = self.values[0]
        await settings.save()

        # If this select is rendered inside one of our LayoutView-based settings screens,
        # recreate the select and force a full rerender to clear Discord's stale selected state.
        if isinstance(self.view, ui.LayoutView) and self.view.children:
            container = cast("ui.Container", self.view.children[0])
            selector_row = next(
                (
                    row
                    for row in container.children
                    if isinstance(row, discord.ui.ActionRow) and self in row.children
                ),
                None,
            )
            if selector_row is not None:
                selector = LangSelector(current=settings.lang, settings_type=self.settings_type)
                self.view.replace_child(
                    container,
                    old_child=selector_row,
                    new_child=discord.ui.ActionRow(selector, id=getattr(selector_row, "id", None)),
                )

                hard_rerender = getattr(self.view, "_hard_rerender", None)
                if callable(hard_rerender):
                    await cast("Any", hard_rerender)(i)
                    return

        await i.response.defer()


class FixModeSelector(ui.Select):
    def __init__(
        self, *, current: FixMode | None, lang: str, settings_type: Literal["guild", "user"]
    ) -> None:
        options: list[discord.SelectOption] = []
        if settings_type == "user":
            options.append(
                discord.SelectOption(
                    label=translator.translate("fix_mode_follow_server", lang=lang),
                    value=FOLLOW_GUILD_VALUE,
                    default=current is None,
                )
            )
        options.extend(
            discord.SelectOption(
                label=translator.translate(f"fix_mode_{mode.value}", lang=lang),
                description=translator.translate(f"fix_mode_{mode.value}_desc", lang=lang),
                value=mode.value,
                default=mode is current,
            )
            for mode in FixMode
        )
        super().__init__(options=options)
        self.settings_type: Literal["guild", "user"] = settings_type

    async def callback(self, i: Interaction) -> None:
        value = self.values[0]

        if self.settings_type == "guild":
            if i.guild_id is None:
                return
            guild_settings, _ = await GuildSettings.get_or_create(id=i.guild_id)
            guild_settings.fix_mode = FixMode(value)
            await guild_settings.save(update_fields=("fix_mode",))
        else:
            user_settings, _ = await UserSettings.get_or_create(id=i.user.id)
            user_settings.fix_mode = None if value == FOLLOW_GUILD_VALUE else FixMode(value)
            await user_settings.save(update_fields=("fix_mode",))

        for option in self.options:
            option.default = option.value == value

        await i.response.edit_message(view=self.view)


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
        if self.settings_type == "guild" and i.guild_id is None:
            return

        await i.response.defer()
        settings_cls = GuildSettings if self.settings_type == "guild" else UserSettings
        settings, _ = await settings_cls.get_or_create(
            id=i.user.id if self.settings_type == "user" else i.guild_id  # pyright: ignore[reportArgumentType]
        )
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
        heading_level = 1 if settings_type == "guild" else 2
        heading_md = "#" * heading_level
        super().__init__(
            discord.ui.TextDisplay(f"{heading_md} {title}\n{description}"),
            accessory=SettingsToggleButton(
                value=value,
                app_emojis=app_emojis,
                settings_key=settings_key,
                settings_type=settings_type,
            ),
        )
