from __future__ import annotations

import os
from typing import TYPE_CHECKING

from discord.ext import commands, tasks
from loguru import logger

if TYPE_CHECKING:
    from embed_fixer.bot import EmbedFixer

HEARBEAT_URL = os.getenv("HEARTBEAT_URL")
if HEARBEAT_URL is None:
    logger.warning("No heartbeat URL configured, skipping health check.")


class HealthCheck(commands.Cog):
    def __init__(self, bot: EmbedFixer) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        if HEARBEAT_URL is not None:
            self.send_heartbeat.start()

    async def cog_unload(self) -> None:
        if HEARBEAT_URL is not None:
            self.send_heartbeat.cancel()

    @tasks.loop(minutes=1)
    async def send_heartbeat(self) -> None:
        logger.info("Sending heartbeat")
        if HEARBEAT_URL is not None:
            await self.bot.session.get(HEARBEAT_URL)

    @send_heartbeat.before_loop
    async def before_send_heartbeat(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: EmbedFixer) -> None:
    await bot.add_cog(HealthCheck(bot))
