from __future__ import annotations

from typing import TYPE_CHECKING

from discord import app_commands
from discord.app_commands import locale_str
from discord.ext import commands

from ..ui.guild_settings import GuildSettingsView

if TYPE_CHECKING:
    from embed_fixer.bot import EmbedFixer

    from ..bot import Interaction

SETTINGS = (
    "disable_fixes",
    "lang",
    "extract_media_channels",
    "disable_fix_channels",
    "toggle_webhook_reply",
    "disable_image_spoilers",
    "toggle_delete_reaction",
    "show_post_content_channels",
    "use_vxreddit",
)


class SettingsCog(commands.Cog):
    def __init__(self, bot: EmbedFixer) -> None:
        self.bot = bot

    @app_commands.guild_only()
    @app_commands.default_permissions()
    @app_commands.choices(
        setting=[
            app_commands.Choice(name=locale_str(setting), value=setting) for setting in SETTINGS
        ]
    )
    @app_commands.rename(setting=locale_str("setting_param"))
    @app_commands.describe(setting=locale_str("setting_param_desc"))
    @app_commands.command(name="settings", description=locale_str("settings_cmd_desc"))
    async def settings(self, i: Interaction, setting: str) -> None:
        if i.guild is None:
            return
        view = GuildSettingsView(i.user, i.guild, self.bot.translator)
        await view.start(i, setting=setting)


async def setup(bot: EmbedFixer) -> None:
    await bot.add_cog(SettingsCog(bot))
