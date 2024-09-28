from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import sys

import discord
from aiohttp_client_cache.backends.sqlite import SQLiteBackend
from aiohttp_client_cache.session import CachedSession
from dotenv import load_dotenv
from loguru import logger

from embed_fixer.bot import EmbedFixer
from embed_fixer.logging import InterceptHandler

load_dotenv()
env = os.environ["ENV"]


def setup_logger() -> None:
    logger.remove()
    logger.add(sys.stderr, level="INFO" if env == "prod" else "DEBUG")
    logging.basicConfig(handlers=[InterceptHandler()], level=logging.INFO, force=True)
    logger.add("logs/embed_fixer.log", level="DEBUG", rotation="1 week", retention="2 weeks")


async def main() -> None:
    async with (
        CachedSession(cache=SQLiteBackend(expire_after=60 * 60)) as session,
        EmbedFixer(session=session, env=env) as bot,
    ):
        with contextlib.suppress(KeyboardInterrupt, asyncio.CancelledError):
            await bot.start(os.environ["DISCORD_TOKEN"])


if __name__ == "__main__":
    discord.VoiceClient.warn_nacl = False
    setup_logger()

    try:
        import uvloop  # pyright: ignore [reportMissingImports]
    except ImportError:
        asyncio.run(main())
    else:
        uvloop.run(main())
