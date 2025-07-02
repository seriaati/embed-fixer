from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import sys

import aiohttp
import discord
from aiohttp_client_cache.backends.redis import RedisBackend
from aiohttp_client_cache.session import CachedSession
from dotenv import load_dotenv
from loguru import logger

from embed_fixer.bot import EmbedFixer
from embed_fixer.logging import InterceptHandler
from embed_fixer.utils.misc import wrap_task_factory

load_dotenv()
env = os.environ["ENV"]


def setup_logger() -> None:
    logger.remove()
    logger.add(sys.stderr, level="INFO" if env == "prod" else "DEBUG")
    logging.basicConfig(handlers=[InterceptHandler()], level=logging.INFO, force=True)
    logger.add("logs/embed_fixer.log", level="DEBUG", rotation="1 week", retention="2 weeks")


async def main() -> None:
    wrap_task_factory()

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
    }

    if env == "dev":
        session = aiohttp.ClientSession(headers=headers)
    else:
        session = CachedSession(cache=RedisBackend(expire_after=600), headers=headers)

    async with session, EmbedFixer(session=session, env=env) as bot:
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
