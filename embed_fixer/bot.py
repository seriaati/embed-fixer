from __future__ import annotations

import contextlib
from pathlib import Path
from typing import TYPE_CHECKING

import anyio
import discord
from discord.ext import commands
from loguru import logger
from tortoise import Tortoise
from tortoise.exceptions import IntegrityError
from tortoise.expressions import Subquery

from embed_fixer.db_config import TORTOISE_CONFIG

from .models import GuildSettings, GuildSettingsOld, GuildSettingsTable
from .translator import AppCommandTranslator, Translator

if TYPE_CHECKING:
    from aiohttp import ClientSession


__all__ = ("EmbedFixer", "Interaction")

type Interaction = discord.Interaction[EmbedFixer]

intents = discord.Intents(
    guilds=True, emojis=True, messages=True, message_content=True, reactions=True
)
allowed_mentions = discord.AllowedMentions(everyone=False)
permissions = discord.Permissions(
    manage_webhooks=True,
    view_channel=True,
    send_messages=True,
    send_messages_in_threads=True,
    manage_messages=True,
    embed_links=True,
    add_reactions=True,
)
allowed_installs = discord.app_commands.AppInstallationType(guild=True, user=True)
allowed_contexts = discord.app_commands.AppCommandContext(
    guild=True, dm_channel=True, private_channel=True
)


class EmbedFixer(commands.AutoShardedBot):
    def __init__(self, *, session: ClientSession, env: str) -> None:
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            case_insensitive=True,
            allowed_mentions=allowed_mentions,
            help_command=None,
            chunk_guilds_at_startup=False,
            max_messages=None,  # pyright: ignore[reportArgumentType]
            member_cache_flags=discord.MemberCacheFlags.none(),
            allowed_installs=allowed_installs,
            allowed_contexts=allowed_contexts,
        )

        self.session = session
        self.env = env
        self.user: discord.ClientUser
        self.translator = Translator()

    async def setup_hook(self) -> None:
        async for filepath in anyio.Path("embed_fixer/cogs").glob("**/*.py"):
            cog_name = Path(filepath).stem
            if self.env == "dev" and cog_name == "health":
                continue

            try:
                await self.load_extension(f"embed_fixer.cogs.{cog_name}")
                logger.info(f"Loaded cog {cog_name}")
            except Exception:
                logger.exception(f"Failed to load cog {cog_name}")

        await self.load_extension("jishaku")

        await self.translator.load()
        await self.tree.set_translator(AppCommandTranslator(self.translator))

        logger.info(f"Invite: {discord.utils.oauth_url(self.user.id, permissions=permissions)}")

        await Tortoise.init(TORTOISE_CONFIG)
        await Tortoise.generate_schemas()
        await self._migrate_guild_settings()

    async def _migrate_guild_settings(self) -> None:
        old_gs = await GuildSettingsOld.exclude(
            id__in=Subquery(GuildSettingsTable.all().values("id"))
        )
        for old in old_gs:
            new = GuildSettings(
                id=old.id,
                disable_webhook_reply=getattr(old, "disable_webhook_reply", False),
                disabled_fixes=getattr(old, "disabled_fixes", []),
                disabled_domains=getattr(old, "disabled_domains", []),
                disable_fix_channels=getattr(old, "disable_fix_channels", []),
                enable_fix_channels=getattr(old, "enable_fix_channels", []),
                extract_media_channels=getattr(old, "extract_media_channels", []),
                disable_image_spoilers=getattr(old, "disable_image_spoilers", []),
                show_post_content_channels=getattr(old, "show_post_content_channels", []),
                disable_delete_reaction=getattr(old, "disable_delete_reaction", False),
                lang=getattr(old, "lang", None),
                use_vxreddit=getattr(old, "use_vxreddit", False),
                delete_msg_emoji=getattr(old, "delete_msg_emoji", "❌"),
                bot_visibility=getattr(old, "bot_visibility", False),
                funnel_target_channel=getattr(old, "funnel_target_channel", None),
                whitelist_role_ids=getattr(old, "whitelist_role_ids", []),
                translate_target_lang=getattr(old, "translate_target_lang", None),
                show_original_link_btn=getattr(old, "show_original_link_btn", False),
            )
            await new.save()
            logger.info(f"Migrated guild settings for guild {new.id}")

    async def on_guild_join(self, guild: discord.Guild) -> None:
        logger.info(f"Joined guild {guild.name} ({guild.id})")
        with contextlib.suppress(IntegrityError):
            await GuildSettings.create(id=guild.id)

    async def close(self) -> None:
        logger.info("Bot shutting down...")
        await Tortoise.close_connections()
        await super().close()
