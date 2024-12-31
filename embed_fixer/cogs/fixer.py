from __future__ import annotations

import asyncio
import contextlib
import io
import re
from typing import TYPE_CHECKING, Any, Final

import aiohttp
import discord
from discord.ext import commands
from loguru import logger
from seria.utils import clean_url, extract_urls, split_list_to_chunks

from ..fixes import FIX_PATTERNS, FIXES
from ..models import GuildSettings, PixivArtworkInfo
from ..translator import Translator

if TYPE_CHECKING:
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

        message = await channel.fetch_message(payload.message_id)
        if " (Embed Fixer)" not in message.author.display_name:
            return

        guild = message.guild
        if guild is None:
            return

        author = await self._get_original_author(message, guild)

        if author is None:
            return
        if payload.user_id == author.id:
            await message.delete()

    async def _find_fixes(
        self,
        message: discord.Message,
        *,
        disabled_fixes: list[str],
        disable_image_spoilers: list[int],
        extract_media: bool,
        filesize_limit: int,
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
                        domain,
                        clean_url_,
                        spoiler=channel_is_nsfw
                        and message.channel.id not in disable_image_spoilers,
                        filesize_limit=filesize_limit,
                    )
                ):
                    medias.extend(m for m in medias_ if self._get_filesize(m.fp) < filesize_limit)
                    if medias:
                        fix_found = True
                        message.content = message.content.replace(url, "")
                        sauces.append(clean_url_)
                        break

                fix_found = True
                fixed_url = clean_url_.replace(domain, fix)
                message.content = message.content.replace(url, fixed_url)
                break

        return fix_found, medias, sauces

    async def _extract_medias(
        self, domain: str, url: str, *, spoiler: bool = False, filesize_limit: int
    ) -> list[discord.File]:
        media_urls: list[str] = []
        files: dict[str, discord.File] = {}
        result: list[discord.File] = []

        if domain == "pixiv.net":
            artwork_info = await self._fetch_pixiv_artwork_info(url)
            media_urls = artwork_info.image_urls if artwork_info is not None else []
        elif domain in {"twitter.com", "x.com"}:
            media_urls = await self._fetch_twitter_media_urls(url)
        elif domain == "www.iwara.tv":
            media_urls = await self._fetch_iwara_video_urls(url)
        elif domain == "bsky.app":
            media_urls = await self._fetch_bluesky_media_urls(url)
        elif domain == "kemono.su":
            media_urls = await self._fetch_kemono_media_urls(url)

        async with asyncio.TaskGroup() as tg:
            for image_url in media_urls:
                tg.create_task(
                    self._download_media(
                        image_url, files, spoiler=spoiler, filesize_limit=filesize_limit
                    )
                )

        for url_ in media_urls:
            if (file := files.get(url_)) is not None:
                result.append(file)

        return result

    async def _send_fixes(
        self,
        message: discord.Message,
        medias: list[discord.File],
        sauces: list[str],
        *,
        disable_delete_reaction: bool,
    ) -> None:
        files = [await a.to_file() for a in message.attachments]
        files.extend(medias)

        if len(sauces) > 1:
            sauces_str = "\n".join(f"<{sauce}>" for sauce in sauces)
            message.content += f"\n\n||{sauces_str}||"
            sauces.clear()

        if files:
            fix_message = await self._send_files(message, files, sauces, disable_delete_reaction)
        else:
            fix_message = await self._send_message(message, disable_delete_reaction)

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
        files: list[discord.File],
        sauces: list[str],
        disable_delete_reaction: bool,
    ) -> discord.Message | None:
        chunked_files = split_list_to_chunks(files, 10)
        guild_lang = await Translator.get_guild_lang(message.guild)
        fixed_message = None

        for chunk in chunked_files:
            kwargs: dict[str, Any] = {}
            if sauces:
                view = discord.ui.View()
                view.add_item(
                    discord.ui.Button(
                        url=sauces[0], label=self.bot.translator.get(guild_lang, "sauce")
                    )
                )
                kwargs["view"] = view

            if isinstance(message.channel, discord.TextChannel):
                webhook = await self._get_or_create_webhook(message)
                fixed_message = await self._send_webhook(message, webhook, files=chunk, **kwargs)
            else:
                fixed_message = await message.channel.send(
                    message.content, tts=message.tts, files=chunk, **kwargs
                )

            message.content = ""

            if not disable_delete_reaction:
                await fixed_message.add_reaction(DELETE_MSG_EMOJI)

        return fixed_message

    async def _send_message(
        self, message: discord.Message, disable_delete_reaction: bool
    ) -> discord.Message:
        if isinstance(message.channel, discord.TextChannel):
            webhook = await self._get_or_create_webhook(message)
            fixed_message = await self._send_webhook(message, webhook)
        else:
            fixed_message = await message.channel.send(message.content, tts=message.tts)

        if not disable_delete_reaction:
            await fixed_message.add_reaction(DELETE_MSG_EMOJI)

        return fixed_message

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
        self, message: discord.Message, webhook: discord.Webhook, **kwargs: Any
    ) -> discord.Message:
        try:
            return await webhook.send(
                message.content,
                username=f"{message.author.display_name} (Embed Fixer)",
                avatar_url=message.author.display_avatar.url,
                tts=message.tts,
                wait=True,
                **kwargs,
            )
        except Exception:
            logger.exception("Failed to send webhook message")
            return await message.channel.send(message.content, tts=message.tts, **kwargs)

    async def _get_or_create_webhook(self, message: discord.Message) -> discord.Webhook:
        if not isinstance(message.channel, discord.TextChannel):
            msg = "Only text channels are supported for webhook creation"
            raise TypeError(msg)

        webhooks = await message.channel.webhooks()
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
        return PixivArtworkInfo(tags=data["tags"], image_urls=data["image_proxy_urls"])

    async def _fetch_twitter_media_urls(self, url: str) -> list[str]:
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
                return []

            data = await response.json()
            tweet = data["tweet"]
            medias = tweet.get("media")
            if medias is None:
                return []

            urls = [media["url"] for media in medias["all"] if media["type"] in allowed_media_types]
            if media_index is not None:
                return [urls[media_index]]
            return urls

    async def _fetch_bluesky_media_urls(self, url: str) -> list[str]:
        api_url = url.replace("bsky.app", "bskx.app") + "/json"

        async with self.bot.session.get(api_url) as response:
            if response.status != 200:
                return []

            data = await response.json()
            if not data["posts"]:
                return []

            urls: list[str] = []
            post = data["posts"][0]
            embed = post.get("embed")

            if embed is None:
                return []

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

            return urls

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
        video_id = url.split("/")[-2]
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

        guild_settings, _ = await GuildSettings.get_or_create(id=message.guild.id)
        if message.channel.id in guild_settings.disable_fix_channels:
            return

        fix_found, medias, sauces = await self._find_fixes(
            message,
            disabled_fixes=guild_settings.disabled_fixes,
            extract_media=message.channel.id in guild_settings.extract_media_channels,
            filesize_limit=message.guild.filesize_limit,
            disable_image_spoilers=guild_settings.disable_image_spoilers,
        )

        if fix_found:
            await self._send_fixes(
                message,
                medias,
                sauces,
                disable_delete_reaction=guild_settings.disable_delete_reaction,
            )
            await message.delete()
        elif (
            message.reference is not None  # noqa: PLR0916
            and isinstance(resolved_ref := message.reference.resolved, discord.Message)
            and resolved_ref.webhook_id is not None
            and not message.author.bot
            and message.channel.id not in guild_settings.disable_fix_channels
            and not guild_settings.disable_webhook_reply
        ):
            await self._reply_to_webhook(message, resolved_ref)


async def setup(bot: EmbedFixer) -> None:
    await bot.add_cog(FixerCog(bot))
