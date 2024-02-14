import asyncio
import contextlib
import logging
import os

import discord
from aiohttp_client_cache.backends.sqlite import SQLiteBackend
from aiohttp_client_cache.session import CachedSession
from dotenv import load_dotenv
from seria.logging import setup_logging

from embed_fixer.bot import EmbedFixer

load_dotenv()
env = os.environ["ENV"]

# Disables PyNaCl warning
discord.VoiceClient.warn_nacl = False


async def main() -> None:
    async with CachedSession(cache=SQLiteBackend(expire_after=60 * 60)) as session, EmbedFixer(
        session=session, env=env
    ) as bot:
        with contextlib.suppress(KeyboardInterrupt, asyncio.CancelledError):
            await bot.start(os.environ["DISCORD_TOKEN"])


with setup_logging(logging.INFO, ()):
    try:
        import uvloop  # type: ignore
    except ImportError:
        asyncio.run(main())
    else:
        uvloop.run(main())
