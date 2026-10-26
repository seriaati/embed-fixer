from __future__ import annotations

from typing import TYPE_CHECKING, Final

from loguru import logger

from embed_fixer.core.config import settings
from embed_fixer.models import SponsoredGuild
from embed_fixer.utils.misc import capture_exception

if TYPE_CHECKING:
    import aiohttp
    import discord

SPONSORS_API_URL: Final[str] = "https://api.seria.moe/sponsors"
QUERY_MEMBERS_LIMIT: Final[int] = 100


class SponsorManager:
    """Tracks sponsors and the guilds they unlock sponsor-only features for.

    A guild is unlocked when at least one of its administrators is a sponsor. Every guild
    is unlocked when no sponsors API key is configured (e.g. self-hosted instances).
    """

    def __init__(self) -> None:
        self._sponsor_ids: set[int] | None = None

    @property
    def enabled(self) -> bool:
        return settings.sponsors_api_key is not None

    async def refresh(self, session: aiohttp.ClientSession) -> None:
        """Fetch the sponsor list, keeping the previous one if the request fails."""
        if settings.sponsors_api_key is None:
            return

        try:
            async with session.get(
                SPONSORS_API_URL, headers={"x-api-key": settings.sponsors_api_key}
            ) as resp:
                resp.raise_for_status()
                sponsors: list[dict[str, str]] = await resp.json()
        except Exception as e:
            capture_exception(e)
            return

        self._sponsor_ids = {int(sponsor["id"]) for sponsor in sponsors}
        logger.info(f"Loaded {len(self._sponsor_ids)} sponsors")

    async def find_admin_sponsor(self, guild: discord.Guild) -> int | None:
        """Find an administrator of the guild who is a sponsor, returning their ID."""
        if not self._sponsor_ids:
            return None

        sponsor_ids = list(self._sponsor_ids)
        for start in range(0, len(sponsor_ids), QUERY_MEMBERS_LIMIT):
            members = await guild.query_members(
                user_ids=sponsor_ids[start : start + QUERY_MEMBERS_LIMIT], limit=QUERY_MEMBERS_LIMIT
            )
            for member in members:
                if member.guild_permissions.administrator:
                    return member.id

        return None

    async def unlock_guild(self, guild: discord.Guild) -> bool:
        """Unlock sponsor-only features for the guild if one of its administrators is a sponsor."""
        if not self.enabled:
            return True

        sponsor_id = await self.find_admin_sponsor(guild)
        if sponsor_id is None:
            return False

        await SponsoredGuild.update_or_create(id=guild.id, defaults={"sponsor_id": sponsor_id})
        return True

    @staticmethod
    async def remove_guild(guild_id: int) -> None:
        """Stop tracking the guild, e.g. when its sponsor-only feature is disabled."""
        await SponsoredGuild.filter(id=guild_id).delete()

    async def is_guild_unlocked(self, guild_id: int) -> bool:
        if not self.enabled:
            return True
        return await SponsoredGuild.filter(id=guild_id, sponsor_id__isnull=False).exists()

    async def revalidate_guilds(self, bot: discord.Client) -> None:
        """Re-check the administrator sponsor of every tracked guild.

        Guilds whose sponsor lapsed, left, or lost administrator are relocked unless another
        administrator is a sponsor, and relocked guilds are unlocked again once one is.
        """
        if self._sponsor_ids is None:
            return

        for sponsored_guild in await SponsoredGuild.all():
            guild = bot.get_guild(sponsored_guild.id)
            if guild is None:
                continue

            try:
                sponsor_id = await self.find_admin_sponsor(guild)
            except Exception as e:
                capture_exception(e)
                continue

            if sponsor_id != sponsored_guild.sponsor_id:
                sponsored_guild.sponsor_id = sponsor_id
                await sponsored_guild.save(update_fields=("sponsor_id",))


sponsors = SponsorManager()
