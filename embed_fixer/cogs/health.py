from __future__ import annotations

import os
from typing import TYPE_CHECKING

import aiohttp
from discord.ext import commands, tasks
from loguru import logger

if TYPE_CHECKING:
    from embed_fixer.bot import EmbedFixer


class HealthCheck(commands.Cog):
    def __init__(self, bot: EmbedFixer) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        self.send_heartbeat.start()

    async def cog_unload(self) -> None:
        self.send_heartbeat.cancel()

    @tasks.loop(minutes=1)
    async def send_heartbeat(self) -> None:
        url = os.getenv("HEARTBEAT_URL")
        if url is None:
            logger.warning("No heartbeat URL configured, skipping health check.")
            return

        async with aiohttp.ClientSession() as session:
            await session.get(url)

    @send_heartbeat.before_loop
    async def before_send_heartbeat(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: EmbedFixer) -> None:
    await bot.add_cog(HealthCheck(bot))
