from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands, tasks
from loguru import logger

from embed_fixer.core.config import settings

if TYPE_CHECKING:
    from embed_fixer.bot import EmbedFixer

HEARTBEAT_URL = settings.heartbeat_url
if HEARTBEAT_URL is None:
    logger.warning("No heartbeat URL configured, skipping health check.")


class HealthCheck(commands.Cog):
    def __init__(self, bot: EmbedFixer) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        if HEARTBEAT_URL is not None:
            self.send_heartbeat.start()

    async def cog_unload(self) -> None:
        if HEARTBEAT_URL is not None:
            self.send_heartbeat.cancel()

    @tasks.loop(minutes=1)
    async def send_heartbeat(self) -> None:
        if HEARTBEAT_URL is not None:
            try:
                async with self.bot.session.get(HEARTBEAT_URL) as resp:
                    if resp.status != 200:
                        logger.error(f"Heartbeat ping returned non-200 status code: {resp.status}")
            except Exception as e:
                logger.error(f"Error sending heartbeat ping: {e}")

    @send_heartbeat.before_loop
    async def before_send_heartbeat(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: EmbedFixer) -> None:
    await bot.add_cog(HealthCheck(bot))
