from __future__ import annotations

from typing import TYPE_CHECKING

from discord import app_commands
from discord.app_commands import locale_str
from discord.ext import commands

from ..embed import DefaultEmbed

if TYPE_CHECKING:
    from embed_fixer.bot import EmbedFixer

    from ..bot import Interaction


class InfoCog(commands.Cog):
    def __init__(self, bot: EmbedFixer) -> None:
        self.bot = bot

    @app_commands.command(name="info", description=locale_str("info_cmd_desc"))
    async def settings(self, i: Interaction) -> None:
        lang = await self.bot.translator.get_guild_lang(i.guild)
        embed = DefaultEmbed(
            title="Embed Fixer", description=self.bot.translator.get(lang, "info_embed_desc")
        )
        embed.set_image(url="https://i.imgur.com/919Gum1.png")
        await i.response.send_message(embed=embed)


async def setup(bot: EmbedFixer) -> None:
    await bot.add_cog(InfoCog(bot))
