from __future__ import annotations

from typing import TYPE_CHECKING

from discord import app_commands
from discord.app_commands import locale_str
from discord.ext import commands

from embed_fixer.models import GuildSettings
from embed_fixer.settings import Setting
from embed_fixer.ui.guild_settings import DeleteMsgEmojiModal, GuildSettingsView

if TYPE_CHECKING:
    from embed_fixer.bot import EmbedFixer, Interaction


class SettingsCog(commands.Cog):
    def __init__(self, bot: EmbedFixer) -> None:
        self.bot = bot

    @app_commands.guild_only()
    @app_commands.default_permissions()
    @app_commands.choices(
        setting=[
            app_commands.Choice(name=locale_str(setting), value=setting) for setting in Setting
        ]
    )
    @app_commands.rename(setting=locale_str("setting_param"))
    @app_commands.describe(setting=locale_str("setting_param_desc"))
    @app_commands.command(name="settings", description=locale_str("settings_cmd_desc"))
    async def settings(self, i: Interaction, setting: Setting) -> None:
        if i.guild is None:
            return

        if setting is Setting.DELETE_MSG_EMOJI:
            settings, _ = await GuildSettings.get_or_create(id=i.guild.id)
            await i.response.send_modal(
                DeleteMsgEmojiModal(i.guild, self.bot.translator, settings=settings)
            )
            return

        view = GuildSettingsView(i.user, i.guild, self.bot.translator)
        await view.start(i, setting=setting)


async def setup(bot: EmbedFixer) -> None:
    await bot.add_cog(SettingsCog(bot))
