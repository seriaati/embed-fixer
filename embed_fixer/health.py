from __future__ import annotations

from typing import TYPE_CHECKING, Self

from aiohttp import web
from loguru import logger

if TYPE_CHECKING:
    import discord


class HealthCheckServer:
    def __init__(self, bot: discord.AutoShardedClient) -> None:
        self.bot = bot
        self.app = web.Application()
        self.runner: web.AppRunner | None = None
        self.site: web.TCPSite | None = None

    async def __aenter__(self) -> Self:
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        await self.stop()

    async def health(self, _request: web.Request) -> web.Response:
        if self.bot.shards:
            all_ready = all(not shard.is_closed() for shard in self.bot.shards.values())
            if all_ready:
                return web.Response(text="OK", status=200)
        return web.Response(text="Not Ready", status=503)

    async def start(self, *, port: int = 8080) -> None:
        self.app.add_routes([web.get("/health", self.health)])
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, "127.0.0.1", port)
        await self.site.start()

        logger.info(f"Health check server started on port {port}")

    async def stop(self) -> None:
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()

        logger.info("Health check server stopped")
