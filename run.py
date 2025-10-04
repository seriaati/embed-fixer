from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import sys

import discord
import sentry_sdk
from aiohttp_client_cache.backends.redis import RedisBackend
from aiohttp_client_cache.backends.sqlite import SQLiteBackend
from aiohttp_client_cache.session import CachedSession
from loguru import logger

from embed_fixer.bot import EmbedFixer
from embed_fixer.core.config import settings
from embed_fixer.utils.logging import InterceptHandler
from embed_fixer.utils.misc import get_project_version, wrap_task_factory

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
}
EXPIRE_AFTER = 600  # seconds


def setup_logger() -> None:
    logger.remove()
    logger.add(sys.stderr, level="INFO" if settings.env == "prod" else "DEBUG")
    logging.basicConfig(handlers=[InterceptHandler()], level=logging.INFO, force=True)
    logger.add("logs/embed_fixer.log", level="DEBUG", rotation="1 week", retention="2 weeks")


def setup_sentry() -> None:
    if settings.sentry_dsn is None:
        logger.warning("No Sentry DSN configured, skipping Sentry setup.")
        return

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.env,
        release=get_project_version(),
        enable_logs=True,
    )


async def main() -> None:
    wrap_task_factory()

    if settings.redis_url is None:
        session = CachedSession(cache=SQLiteBackend(expire_after=EXPIRE_AFTER), headers=HEADERS)
    else:
        session = CachedSession(
            cache=RedisBackend(expire_after=EXPIRE_AFTER, address=settings.redis_url),
            headers=HEADERS,
        )

    async with session, EmbedFixer(session=session, env=settings.env) as bot:
        with contextlib.suppress(KeyboardInterrupt, asyncio.CancelledError):
            await bot.start(os.environ["DISCORD_TOKEN"])


if __name__ == "__main__":
    discord.VoiceClient.warn_nacl = False
    setup_logger()
    setup_sentry()

    try:
        import uvloop  # pyright: ignore [reportMissingImports]
    except ImportError:
        asyncio.run(main())
    else:
        uvloop.run(main())
