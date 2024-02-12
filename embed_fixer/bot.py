import contextlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING, TypeAlias

import discord
from discord.ext import commands
from tortoise import Tortoise
from tortoise.exceptions import IntegrityError

from .models import GuildSettings
from .translator import AppCommandTranslator, Translator

if TYPE_CHECKING:
    from aiohttp import ClientSession

LOGGER_ = logging.getLogger(__name__)

__all__ = ("EmbedFixer", "INTERACTION")

INTERACTION: TypeAlias = discord.Interaction["EmbedFixer"]

intents = discord.Intents(
    guilds=True,
    members=True,
    emojis=True,
    messages=True,
    message_content=True,
)
allowed_mentions = discord.AllowedMentions(
    users=True,
    everyone=False,
    roles=False,
    replied_user=False,
)


class EmbedFixer(commands.AutoShardedBot):
    def __init__(
        self,
        *,
        session: "ClientSession",
        env: str,
    ) -> None:
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            case_insensitive=True,
            allowed_mentions=allowed_mentions,
            help_command=None,
            chunk_guilds_at_startup=False,
            max_messages=None,
            member_cache_flags=discord.MemberCacheFlags.none(),
        )

        self.session = session
        self.env = env
        self.user: discord.ClientUser
        self.translator = Translator()

    async def setup_hook(self) -> None:
        for filepath in Path("embed_fixer/cogs").glob("**/*.py"):
            cog_name = Path(filepath).stem
            try:
                await self.load_extension(f"embed_fixer.cogs.{cog_name}")
                LOGGER_.info("Loaded cog %r", cog_name)
            except Exception:
                LOGGER_.exception("Failed to load cog %r", cog_name)

        await self.load_extension("jishaku")

        await self.translator.load()
        await self.tree.set_translator(AppCommandTranslator(self.translator))

        await Tortoise.init(
            {
                "connections": {"default": "sqlite://embed_fixer.db"},
                "apps": {"embed_fixer": {"models": ["embed_fixer.models"]}},
            }
        )
        await Tortoise.generate_schemas()

    async def on_guild_join(self, guild: discord.Guild) -> None:
        LOGGER_.info("Joined guild %r", guild)
        with contextlib.suppress(IntegrityError):
            await GuildSettings.create(id=guild.id)

    async def close(self) -> None:
        LOGGER_.info("Bot shutting down...")
        await Tortoise.close_connections()
        await super().close()
