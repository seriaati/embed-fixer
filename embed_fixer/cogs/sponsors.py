from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands, tasks

from embed_fixer.utils.sponsors import sponsors

if TYPE_CHECKING:
    from embed_fixer.bot import EmbedFixer


class SponsorsCog(commands.Cog):
    def __init__(self, bot: EmbedFixer) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        if sponsors.enabled:
            self._refresh_sponsors.start()

    async def cog_unload(self) -> None:
        self._refresh_sponsors.cancel()

    @tasks.loop(hours=1)
    async def _refresh_sponsors(self) -> None:
        await sponsors.refresh(self.bot.session)
        await sponsors.revalidate_guilds(self.bot)

    @_refresh_sponsors.before_loop
    async def _before_refresh_sponsors(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: EmbedFixer) -> None:
    await bot.add_cog(SponsorsCog(bot))
