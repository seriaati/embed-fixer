import asyncio
import contextlib
import os

import aiohttp
import discord
from dotenv import load_dotenv

from embed_fixer.bot import EmbedFixer
from embed_fixer.logging import setup_logging

load_dotenv()
env = os.environ["ENV"]

# Disables PyNaCl warning
discord.VoiceClient.warn_nacl = False


async def main() -> None:
    async with aiohttp.ClientSession() as session, EmbedFixer(session=session, env=env) as bot:
        with contextlib.suppress(KeyboardInterrupt, asyncio.CancelledError):
            await bot.start(os.environ["DISCORD_TOKEN"])


with setup_logging(env):
    try:
        import uvloop  # type: ignore
    except ImportError:
        asyncio.run(main())
    else:
        uvloop.run(main())
