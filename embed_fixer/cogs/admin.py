from __future__ import annotations

from typing import TYPE_CHECKING, Any

from discord.ext import commands

if TYPE_CHECKING:
    from discord.ext.commands.context import Context

    from ..bot import EmbedFixer


class Admin(commands.Cog):
    def __init__(self, bot: EmbedFixer) -> None:
        self.bot = bot

    async def cog_check(self, ctx: Context) -> bool:
        return await self.bot.is_owner(ctx.author)

    @commands.command(name="sync")
    async def sync_command(self, ctx: commands.Context) -> Any:
        message = await ctx.send("Syncing commands...")
        synced_commands = await self.bot.tree.sync()
        await message.edit(content=f"Synced {len(synced_commands)} commands.")


async def setup(bot: EmbedFixer) -> None:
    await bot.add_cog(Admin(bot))
