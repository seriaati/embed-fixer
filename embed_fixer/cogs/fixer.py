from __future__ import annotations

import asyncio
import contextlib
import io
import itertools
import re
from typing import TYPE_CHECKING, Any, Final

import aiohttp
import discord
from discord.ext import commands
from loguru import logger
from seria.utils import clean_url, extract_urls

from ..fixes import FIX_PATTERNS, FIXES
from ..models import (
    BlueskyPostInfo,
    FindFixResult,
    GuildSettings,
    Media,
    PixivArtworkInfo,
    PostExtractionResult,
    TwitterPostInfo,
)
from ..translator import Translator

if TYPE_CHECKING:
    from collections.abc import Sequence

    from embed_fixer.bot import EmbedFixer

DELETE_MSG_EMOJI: Final[str] = "❌"


class FixerCog(commands.Cog):
    def __init__(self, bot: EmbedFixer) -> None:
        self.bot = bot

    @staticmethod
    def _get_filesize(fp: io.BufferedIOBase) -> int:
        original_pos = fp.tell()
        fp.seek(0, io.SEEK_END)
        size = fp.tell()
        fp.seek(original_pos)
        return size

    @staticmethod
    async def _get_original_author(
        message: discord.Message, guild: discord.Guild
    ) -> discord.Member | None:
        authors = await guild.query_members(
            message.author.display_name.removesuffix(" (Embed Fixer)")
        )
        if not authors:
            return None

        return authors[0]

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        if payload.user_id == self.bot.user.id or payload.emoji.name != DELETE_MSG_EMOJI:
            return

        channel = self.bot.get_channel(payload.channel_id)
        if not isinstance(channel, discord.TextChannel | discord.Thread):
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.Forbidden:
            logger.warning(
                f"Failed to fetch message in {channel!r}, bot perms: {channel.permissions_for(channel.guild.me)}"
            )
            return

        if " (Embed Fixer)" not in message.author.display_name:
            return

        guild = message.guild
        if guild is None:
            return

        author = await self._get_original_author(message, guild)

        if author is None:
            return
        if payload.user_id == author.id:
            try:
                await message.delete()
            except discord.Forbidden:
                logger.warning(f"Failed to delete message in {channel!r} in {guild!r}")
                await message.reply(
                    self.bot.translator.get(
                        await Translator.get_guild_lang(guild), "no_perms_to_delete_msg"
                    )
                )

    async def _find_fixes(
        self,
        message: discord.Message,
        *,
        disabled_fixes: list[str],
        disable_image_spoilers: list[int],
        extract_media: bool,
        filesize_limit: int,
    ) -> FindFixResult:
        channel_id = message.channel.id

        fix_found = False
        medias: list[Media] = []
        sauces: list[str] = []
        content = ""
        author_md = ""

        channel_is_nsfw = isinstance(message.channel, discord.TextChannel) and message.channel.nsfw
        urls = extract_urls(message.content, clean=False)

        for url in urls:
            clean_url_ = clean_url(url).replace("www.", "")
            if not any(re.match(pattern, clean_url_) for pattern in FIX_PATTERNS):
                continue

            for domain, fix in FIXES.items():
                if domain in disabled_fixes or domain not in url:
                    continue

                if domain == "pixiv.net" and not await self._is_valid_pixiv_url(
                    clean_url_, channel_is_nsfw
                ):
                    break

                if extract_media:
                    result = await self._extract_post_info(
                        domain,
                        url,
                        spoiler=channel_is_nsfw and channel_id not in disable_image_spoilers,
                        filesize_limit=filesize_limit,
                    )
                    medias.extend(
                        Media(url=media.url)
                        if (media.file and self._get_filesize(media.file.fp) > filesize_limit)
                        else media
                        for media in result.medias
                    )
                    content, author_md = result.content, result.author_md

                    if medias:
                        fix_found = True
                        message.content = message.content.replace(url, "")
                        sauces.append(clean_url_)
                        break

                fix_found = True
                message.content = message.content.replace(url, clean_url_.replace(domain, fix))
                break

        return FindFixResult(
            fix_found=fix_found, medias=medias, sauces=sauces, content=content, author_md=author_md
        )

    async def _is_valid_pixiv_url(self, url: str, channel_is_nsfw: bool) -> bool:
        artwork_info = await self._fetch_pixiv_artwork_info(url)
        return not (artwork_info and "#R-18" in artwork_info.tags and not channel_is_nsfw)

    async def _extract_post_info(
        self, domain: str, url: str, *, spoiler: bool = False, filesize_limit: int
    ) -> PostExtractionResult:
        media_urls: list[str] = []
        downloaded_files: dict[str, discord.File] = {}
        medias: list[Media] = []
        content = ""

        info = None

        if domain == "pixiv.net":
            info = await self._fetch_pixiv_artwork_info(url)
            content = info.description if info is not None else ""
            media_urls = info.image_urls if info is not None else []
        elif domain in {"twitter.com", "x.com"}:
            info = await self._fetch_twitter_post_info(url)
            content = info.content if info is not None else ""
            media_urls = info.media_urls if info is not None else []
        elif domain == "iwara.tv":
            media_urls = await self._fetch_iwara_video_urls(url)
        elif domain == "bsky.app":
            info = await self._fetch_bluesky_post_info(url)
            content = info.content if info is not None else ""
            media_urls = info.media_urls if info is not None else []
        elif domain == "kemono.su":
            media_urls = await self._fetch_kemono_media_urls(url)

        async with asyncio.TaskGroup() as tg:
            for image_url in media_urls:
                tg.create_task(
                    self._download_media(
                        image_url, downloaded_files, spoiler=spoiler, filesize_limit=filesize_limit
                    )
                )

        for media_url in media_urls:
            file_ = downloaded_files.get(media_url)
            medias.append(Media(url=media_url, file=file_))

        return PostExtractionResult(
            medias=medias,
            content=content[:2000],
            author_md=info.author_md if info is not None else "",
        )

    async def _send_fixes(
        self,
        message: discord.Message,
        result: FindFixResult,
        *,
        disable_delete_reaction: bool,
        show_post_content: bool,
    ) -> None:
        medias, sauces = result.medias, result.sauces
        medias.extend([Media(url=a.url, file=await a.to_file()) for a in message.attachments])

        if show_post_content:
            if result.author_md:
                message.content += f"\n-# {result.author_md}"
            if result.content:
                message.content += f"\n{result.content}"

        if len(sauces) > 1:
            sauces_str = "\n".join(f"<{sauce}>" for sauce in sauces)
            message.content += f"\n||{sauces_str}||"
            sauces.clear()

        if medias:
            fix_message = await self._send_files(
                message, medias, sauces, disable_delete_reaction=disable_delete_reaction
            )
        else:
            fix_message = await self._send_message(
                message, disable_delete_reaction=disable_delete_reaction
            )

        if (
            message.reference is not None
            and isinstance(resolved_ref := message.reference.resolved, discord.Message)
            and message.guild is not None
            and fix_message is not None
        ):
            await self._reply_to_resolved_message(fix_message, resolved_ref)

    async def _send_files(
        self,
        message: discord.Message,
        medias: list[Media],
        sauces: list[str],
        *,
        disable_delete_reaction: bool,
    ) -> discord.Message | None:
        """Send multiple files in batches of 10."""
        guild_lang: str | None = None
        fix_message = None

        for chunk in itertools.batched(medias, 10):
            kwargs: dict[str, Any] = {}
            if sauces:
                if guild_lang is None:
                    guild_lang = await Translator.get_guild_lang(message.guild)

                view = discord.ui.View()
                view.add_item(
                    discord.ui.Button(
                        url=sauces[0], label=self.bot.translator.get(guild_lang, "sauce")
                    )
                )
                kwargs["view"] = view

            files: list[discord.File] = []
            for media in chunk:
                if media.file is not None:
                    files.append(media.file)
                else:
                    message.content += f"\n{media.url}"

            fix_message = await self._send_message(
                message, disable_delete_reaction=disable_delete_reaction, medias=chunk, **kwargs
            )

            message.content = ""

        return fix_message

    async def _send_message(
        self,
        message: discord.Message,
        *,
        disable_delete_reaction: bool,
        medias: Sequence[Media] | None = None,
        **kwargs: Any,
    ) -> discord.Message:
        """Send a message with a webhook if possible, otherwise send a regular message."""
        webhook = await self._get_or_create_webhook(message)
        medias = medias or []
        files = [media.file for media in medias if media.file is not None]

        try:
            if webhook is not None:
                fix_message = await self._send_webhook(message, webhook, files=files, **kwargs)
            else:
                fix_message = await message.channel.send(
                    message.content, tts=message.tts, files=files, **kwargs
                )
        except discord.HTTPException as e:
            if e.code != 40005:
                raise

            message.content += "\n".join(media.url for media in medias)
            fix_message = await self._send_message(
                message, disable_delete_reaction=disable_delete_reaction, **kwargs
            )

        if not disable_delete_reaction:
            await fix_message.add_reaction(DELETE_MSG_EMOJI)

        return fix_message

    async def _reply_to_resolved_message(
        self, message: discord.Message, resolved_ref: discord.Message
    ) -> None:
        if message.guild is None:
            return

        author = await self._get_original_author(resolved_ref, message.guild)
        if author is not None:
            await message.reply(
                self.bot.translator.get(
                    await Translator.get_guild_lang(message.guild),
                    "replying_to",
                    user=author.mention,
                    url=resolved_ref.jump_url,
                )
            )

    async def _send_webhook(
        self,
        message: discord.Message,
        webhook: discord.Webhook,
        files: list[discord.File] | None = None,
        **kwargs: Any,
    ) -> discord.Message:
        files = files or []
        try:
            return await webhook.send(
                message.content,
                username=f"{message.author.display_name} (Embed Fixer)",
                avatar_url=message.author.display_avatar.url,
                tts=message.tts,
                wait=True,
                files=files,
                **kwargs,
            )
        except discord.HTTPException:
            raise
        except Exception:
            logger.exception("Failed to send webhook message")
            await message.channel.send(
                self.bot.translator.get(
                    await Translator.get_guild_lang(message.guild), "failed_to_send_webhook"
                )
            )
            raise

    async def _get_or_create_webhook(self, message: discord.Message) -> discord.Webhook | None:
        if not isinstance(message.channel, discord.TextChannel):
            return None

        try:
            webhooks = await message.channel.webhooks()
        except discord.Forbidden:
            await message.channel.send(
                self.bot.translator.get(
                    await Translator.get_guild_lang(message.guild), "no_perms_to_manage_webhooks"
                )
            )
            return None

        webhook_name = self.bot.user.name
        webhook = discord.utils.get(webhooks, name=webhook_name)
        if webhook is None:
            webhook = await message.channel.create_webhook(
                name=webhook_name, avatar=await self.bot.user.display_avatar.read()
            )

        return webhook

    async def _fetch_pixiv_artwork_info(self, url: str) -> PixivArtworkInfo | None:
        artwork_id = url.split("/")[-1]
        api_url = f"https://phixiv.net/api/info?id={artwork_id}"
        async with self.bot.session.get(api_url) as response:
            if response.status != 200:
                return None

            data = await response.json()

        if "image_proxy_urls" not in data:
            return None

        return PixivArtworkInfo(
            tags=data.get("tags", []),
            image_urls=data["image_proxy_urls"],
            description=data.get("description", ""),
            author_name=data.get("author_name", ""),
            author_id=data.get("author_id", ""),
        )

    async def _fetch_twitter_post_info(self, url: str) -> TwitterPostInfo | None:
        if "twitter.com" in url:
            api_url = url.replace("twitter.com", "api.fxtwitter.com")
        else:
            api_url = url.replace("x.com", "api.fxtwitter.com")

        allowed_media_types = {"photo", "video", "gif"}
        media_index = None

        if "photo" in api_url or "video" in api_url:
            allowed_media_types = {api_url.split("/")[-2]}
            media_index = int(api_url.split("/")[-1]) - 1
            api_url = "/".join(api_url.split("/")[:-2])

        async with self.bot.session.get(api_url) as response:
            if response.status != 200:
                return None

            data = await response.json()
            tweet = data["tweet"]
            medias = tweet.get("media")
            author = tweet.get("author")
            if medias is None or author is None:
                return None

            urls = [media["url"] for media in medias["all"] if media["type"] in allowed_media_types]
            media_urls = (
                [urls[media_index]] if media_index is not None and len(urls) > media_index else urls
            )
            return TwitterPostInfo(
                media_urls=media_urls,
                content=tweet.get("text", ""),
                author_name=author.get("name", ""),
                author_handle=author.get("screen_name", ""),
            )

    async def _fetch_bluesky_post_info(self, url: str) -> BlueskyPostInfo | None:
        api_url = url.replace("bsky.app", "bskx.app") + "/json"

        async with self.bot.session.get(api_url) as response:
            if response.status != 200:
                return None

            data = await response.json()
            if not data["posts"]:
                return None

            urls: list[str] = []
            post = data["posts"][0]
            embed = post.get("embed")
            author = post.get("author")

            if embed is None or author is None:
                return None

            # Image
            if (images := embed.get("images")) is not None:
                urls.extend(image["fullsize"] for image in images)

            # Video
            if (
                (cid := embed.get("cid")) is not None
                and (author := post.get("author")) is not None
                and (did := author.get("did"))
            ):
                urls.append(
                    f"https://bsky.social/xrpc/com.atproto.sync.getBlob?cid={cid}&did={did}"
                )

            # External GIF
            if (external := (embed.get("external"))) and (uri := external.get("uri")):
                urls.append(uri)

            return BlueskyPostInfo(
                media_urls=urls,
                content=post.get("text", ""),
                author_name=author.get("displayName", ""),
                author_handle=author.get("handle", ""),
            )

    async def _fetch_kemono_media_urls(self, url: str) -> list[str]:
        urls: list[str] = []
        api_url = url.replace("kemono.su", "kemono.su/api/v1")

        async with self.bot.session.get(api_url) as resp:
            data = await resp.json()

        if "attachments" not in data:
            return urls

        attachments: list[dict[str, str]] = data["attachments"]
        for attachment in attachments:
            if attachment["name"].endswith(".mp4"):
                urls.append(f"https://n1.kemono.su/data{attachment['path']}")
            elif attachment["name"].endswith((".jpg", ".jpeg", ".png")):
                urls.append(f"https://img.kemono.su/thumbnail/data{attachment['path']}")
            elif attachment["name"].endswith(".gif"):
                urls.append(f"https://n3.kemono.su/data{attachment['path']}?f={attachment['name']}")

        return urls

    async def _fetch_iwara_video_urls(self, url: str) -> list[str]:
        match = re.search(r"/video/([a-zA-Z0-9]+)/", url)
        video_id = match.group(1) if match else None
        if video_id is None:
            return []
        return [f"https://fxiwara.seria.moe/dl/{video_id}/360"]

    async def _download_media(
        self, url: str, result: dict[str, discord.File], *, spoiler: bool, filesize_limit: int
    ) -> None:
        timeout = aiohttp.ClientTimeout(total=10)
        with contextlib.suppress(Exception):
            async with self.bot.session.get(url, timeout=timeout) as resp:
                if resp.status != 200:
                    return None

                content_length = resp.headers.get("Content-Length")
                if content_length is not None and int(content_length) > filesize_limit:
                    return None

                data = await resp.read()

                media_type = resp.headers.get("Content-Type")

            if media_type:
                filename = f"{url.split('/')[-1].split('.')[0]}.{media_type.split('/')[-1]}"
            else:
                filename = url.split("/")[-1]

            result[url] = discord.File(io.BytesIO(data), filename=filename, spoiler=spoiler)

    async def _reply_to_webhook(
        self, message: discord.Message, resolved_ref: discord.Message
    ) -> None:
        guild = message.guild
        if guild is None:
            return

        author = await self._get_original_author(resolved_ref, guild)
        if author is not None and not author.bot:
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

        channel, guild, author = message.channel, message.guild, message.author

        guild_settings, _ = await GuildSettings.get_or_create(id=guild.id)
        if channel.id in guild_settings.disable_fix_channels:
            return

        result = await self._find_fixes(
            message,
            disabled_fixes=guild_settings.disabled_fixes,
            extract_media=channel.id in guild_settings.extract_media_channels,
            filesize_limit=guild.filesize_limit,
            disable_image_spoilers=guild_settings.disable_image_spoilers,
        )

        if result.fix_found:
            await self._send_fixes(
                message,
                result,
                disable_delete_reaction=guild_settings.disable_delete_reaction,
                show_post_content=channel.id in guild_settings.show_post_content_channels,
            )
            try:
                await message.delete()
            except discord.Forbidden:
                logger.warning(f"Failed to delete message in {channel!r} in {guild!r}")
                await message.reply(
                    self.bot.translator.get(
                        await Translator.get_guild_lang(guild), "no_perms_to_delete_msg"
                    )
                )
        elif (
            message.reference is not None  # noqa: PLR0916
            and isinstance(resolved_ref := message.reference.resolved, discord.Message)
            and resolved_ref.webhook_id is not None
            and not author.bot
            and channel.id not in guild_settings.disable_fix_channels
            and not guild_settings.disable_webhook_reply
        ):
            await self._reply_to_webhook(message, resolved_ref)


async def setup(bot: EmbedFixer) -> None:
    await bot.add_cog(FixerCog(bot))
