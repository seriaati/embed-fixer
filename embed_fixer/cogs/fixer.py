import io
import logging
import re
from typing import TYPE_CHECKING

import discord
from discord.ext import commands
from seria.utils import clean_url, extract_urls

from ..fixes import FIX_PATTERNS, FIXES
from ..models import GuildSettings, PixivArtworkInfo
from ..translator import Translator
from ..ui.delete_webhook_msg import DeleteWebhookMsgView

if TYPE_CHECKING:
    from embed_fixer.bot import EmbedFixer

LOGGER_ = logging.getLogger(__name__)


class FixerCog(commands.Cog):
    def __init__(self, bot: "EmbedFixer") -> None:
        self.bot = bot

    async def _find_fixes(
        self,
        message: discord.Message,
        disabled_fixes: list[str],
        extract_media: bool,
    ) -> tuple[bool, list[discord.File], list[str]]:
        fix_found = False
        medias: list[discord.File] = []
        sauces: list[str] = []

        channel_is_nsfw = isinstance(message.channel, discord.TextChannel) and message.channel.nsfw
        urls = extract_urls(message.content, clean=False)

        for url in urls:
            clean_url_ = clean_url(url)
            for pattern in FIX_PATTERNS:
                if re.match(pattern, clean_url_) is not None:
                    break
            else:
                continue

            for domain, fix in FIXES.items():
                if domain in disabled_fixes or domain not in url:
                    continue

                if domain == "pixiv.net":
                    artwork_info = await self._fetch_pixiv_artwork_info(clean_url_)
                    if (
                        artwork_info is not None
                        and "#R-18" in artwork_info.tags
                        and not channel_is_nsfw
                    ):
                        break

                if extract_media and (
                    medias_ := await self._extract_medias(
                        domain, clean_url_, spoiler=channel_is_nsfw
                    )
                ):
                    fix_found = True
                    medias.extend(medias_)
                    message.content = message.content.replace(url, "")
                    sauces.append(clean_url_)
                    break

                fix_found = True
                fixed_url = clean_url_.replace(domain, fix)
                message.content = message.content.replace(url, fixed_url)
                break

        return fix_found, medias, sauces

    async def _extract_medias(
        self, domain: str, url: str, *, spoiler: bool = False
    ) -> list[discord.File]:
        image_urls: list[str] = []

        if domain == "pixiv.net":
            artwork_info = await self._fetch_pixiv_artwork_info(url)
            image_urls = artwork_info.image_urls if artwork_info is not None else []
        elif domain in {"twitter.com", "x.com"}:
            image_urls = await self._fetch_twitter_media_urls(url)

        medias_ = [
            await self._download_media(image_url, spoiler=spoiler) for image_url in image_urls
        ]
        return [media for media in medias_ if media is not None]

    async def _send_fixes(
        self, message: discord.Message, medias: list[discord.File], sauces: list[str]
    ) -> None:
        files = [await a.to_file() for a in message.attachments]
        files.extend(medias)

        view = DeleteWebhookMsgView(message.author, message.guild, self.bot.translator)
        view.message = message
        await view.start(sauces=sauces)
        if len(sauces) > 1:
            sauces_str = "\n".join(f"<{sauce}>" for sauce in sauces)
            message.content += f"\n\n||{sauces_str}||"
            sauces.clear()
        await view.start(sauces=sauces if len(sauces) == 1 else [])

        if isinstance(message.channel, discord.TextChannel):
            webhooks = await message.channel.webhooks()
            webhook_name = "Embed Fixer"
            webhook = discord.utils.get(webhooks, name=webhook_name)
            if webhook is None:
                webhook = await message.channel.create_webhook(
                    name=webhook_name, avatar=await self.bot.user.display_avatar.read()
                )

            fixed_message = await webhook.send(
                message.content,
                username=f"{message.author.display_name} (Embed Fixer)",
                avatar_url=message.author.display_avatar.url,
                tts=message.tts,
                files=files,
                view=view,
                wait=True,
            )
        else:
            fixed_message = await message.channel.send(
                message.content, tts=message.tts, files=files, view=view
            )

        if (
            message.reference is not None
            and isinstance(resolved_ref := message.reference.resolved, discord.Message)
            and message.guild is not None
        ):
            author = message.guild.get_member_named(
                resolved_ref.author.display_name.removesuffix(" (Embed Fixer)")
            )
            if author:
                await fixed_message.reply(
                    self.bot.translator.get(
                        await Translator.get_guild_lang(message.guild),
                        "replying_to",
                        user=author.mention,
                        url=resolved_ref.jump_url,
                    ),
                    mention_author=False,
                )

    async def _fetch_pixiv_artwork_info(self, url: str) -> PixivArtworkInfo | None:
        artwork_id = url.split("/")[-1]
        api_url = f"https://phixiv.net/api/info?id={artwork_id}"
        async with self.bot.session.get(api_url) as response:
            if response.status != 200:
                return None

            data = await response.json()
        return PixivArtworkInfo(tags=data["tags"], image_urls=data["image_proxy_urls"])

    async def _fetch_twitter_media_urls(self, url: str) -> list[str]:
        if "twitter.com" in url:
            api_url = url.replace("twitter.com", "api.fxtwitter.com")
        else:
            api_url = url.replace("x.com", "api.fxtwitter.com")

        async with self.bot.session.get(api_url) as response:
            if response.status != 200:
                return []

            data = await response.json()
            tweet = data["tweet"]
            medias = tweet.get("media")
            if medias is None:
                return []
            return [media["url"] for media in medias["all"] if media["type"] in {"photo", "video"}]

    async def _download_media(self, url: str, spoiler: bool = False) -> discord.File | None:
        async with self.bot.session.get(url) as response:
            if response.status != 200:
                return None
            data = await response.read()
            filename = url.split("/")[-1].split("?")[0]
            return discord.File(io.BytesIO(data), filename=filename, spoiler=spoiler)

    async def _reply_to_webhook(
        self, message: discord.Message, resolved_ref: discord.Message
    ) -> None:
        guild = message.guild
        if guild is None:
            return

        if not guild.chunked:
            await guild.chunk()

        author = guild.get_member_named(
            resolved_ref.author.display_name.removesuffix(" (Embed Fixer)")
        )
        if author is not None:
            await message.reply(
                self.bot.translator.get(
                    await Translator.get_guild_lang(guild),
                    "replying_to",
                    user=author.mention,
                    url=resolved_ref.jump_url,
                ),
                mention_author=False,
            )

    @commands.Cog.listener("on_message")
    async def embed_fixer(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None:
            return

        guild_settings = await GuildSettings.get_or_none(id=message.guild.id)
        if guild_settings is None:
            LOGGER_.warning("GuildSettings not found for guild %r", message.guild)
            return

        if message.channel.id in guild_settings.disable_fix_channels:
            return

        fix_found, medias, sauces = await self._find_fixes(
            message,
            guild_settings.disabled_fixes,
            message.channel.id in guild_settings.extract_media_channels,
        )

        if fix_found:
            await self._send_fixes(message, medias, sauces)
            await message.delete()
        elif (
            message.reference is not None
            and isinstance(resolved_ref := message.reference.resolved, discord.Message)
            and resolved_ref.webhook_id is not None
            and not message.author.bot
            and message.channel.id not in guild_settings.disable_fix_channels
        ):
            await self._reply_to_webhook(message, resolved_ref)


async def setup(bot: "EmbedFixer") -> None:
    await bot.add_cog(FixerCog(bot))
