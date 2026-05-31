from __future__ import annotations

import asyncio
import contextlib
import logging
import sys
from typing import TYPE_CHECKING

import discord
import sentry_sdk
from aiohttp_client_cache.backends.redis import RedisBackend
from aiohttp_client_cache.backends.sqlite import SQLiteBackend
from aiohttp_client_cache.session import CachedSession
from discord.ext.commands import CommandNotFound
from loguru import logger
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from embed_fixer.bot import EmbedFixer
from embed_fixer.core.config import settings
from embed_fixer.health import HealthCheckServer
from embed_fixer.utils.logging import InterceptHandler
from embed_fixer.utils.misc import get_project_version, wrap_task_factory

if TYPE_CHECKING:
    from sentry_sdk.types import Event, Hint

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
}
EXPIRE_AFTER = 600  # seconds


def setup_logger() -> None:
    logger.disable("aiohttp.web_log")
    logger.remove()
    logger.add(sys.stderr, level="INFO" if settings.env == "prod" else "DEBUG")
    logging.basicConfig(handlers=[InterceptHandler()], level=logging.INFO, force=True)
    logger.add("logs/embed_fixer.log", level="DEBUG", rotation="1 week", retention="2 weeks")


def _is_discord_503(hint: Hint, event: Event) -> bool:
    """Return True if the event is a Discord API 503 Service Unavailable error.

    These are transient upstream failures from Discord and not actionable, so they
    should be dropped instead of cluttering Sentry (e.g. EMBED-FIXER-1W/39/V).
    """
    exc_info = hint.get("exc_info")
    if exc_info is not None and isinstance(exc_info[1], discord.DiscordServerError):
        return exc_info[1].status == 503

    # Fallback for events captured without exc_info (e.g. serialized log records).
    for value in event.get("exception", {}).get("values", []):
        if value.get("type") == "DiscordServerError" and "503" in (value.get("value") or ""):
            return True

    return False


def before_send(event: Event, hint: Hint) -> Event | None:
    if _is_discord_503(hint, event):
        logger.warning("Ignoring Discord API 503 Service Unavailable error.")
        return None
    return event


def setup_sentry() -> None:
    if settings.sentry_dsn is None:
        logger.warning("No Sentry DSN configured, skipping Sentry setup.")
        return

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        integrations=[AsyncioIntegration()],
        disabled_integrations=[LoggingIntegration()],
        environment=settings.env,
        release=get_project_version(),
        enable_logs=True,
        ignore_errors=[CommandNotFound],
        before_send=before_send,
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

    async with (
        session,
        EmbedFixer(session=session, env=settings.env) as bot,
        HealthCheckServer(bot),
    ):
        with contextlib.suppress(KeyboardInterrupt, asyncio.CancelledError):
            await bot.start(settings.discord_token)


if __name__ == "__main__":
    discord.VoiceClient.warn_nacl = False
    setup_logger()
    setup_sentry()

    logger.info(f"Starting EmbedFixer {get_project_version()} in {settings.env!r} environment.")

    try:
        import uvloop
    except ImportError:
        asyncio.run(main())
    else:
        uvloop.run(main())
