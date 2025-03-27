from __future__ import annotations

import itertools
import re
from typing import TYPE_CHECKING, Any, Final

import discord
from discord.ext import commands
from loguru import logger
from seria.utils import clean_url

from embed_fixer.fixes import FIX_PATTERNS, FIXES
from embed_fixer.models import FindFixResult, GuildSettings, Media, PostExtractionResult
from embed_fixer.translator import Translator
from embed_fixer.utils.download_media import MediaDownloader
from embed_fixer.utils.fetch_info import PostInfoFetcher
from embed_fixer.utils.general import extract_urls, get_filesize

if TYPE_CHECKING:
    from collections.abc import Sequence

    from embed_fixer.bot import EmbedFixer

USERNAME_SUFFIX: Final[str] = " (Embed Fixer)"


class FixerCog(commands.Cog):
    def __init__(self, bot: EmbedFixer) -> None:
        self.bot = bot
        self.fetch_info = PostInfoFetcher(self.bot.session)

    @staticmethod
    async def _get_original_author(
        message: discord.Message, guild: discord.Guild
    ) -> discord.Member | None:
        authors = await guild.query_members(
            message.author.display_name.removesuffix(USERNAME_SUFFIX), limit=1
        )
        if not authors:
            return None

        return authors[0]

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:  # noqa: PLR0911
        if payload.guild_id is None:
            return

        settings, _ = await GuildSettings.get_or_create(id=payload.guild_id)
        if payload.user_id == self.bot.user.id or str(payload.emoji) != settings.delete_msg_emoji:
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

        if USERNAME_SUFFIX not in message.author.display_name:
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
        self, message: discord.Message, *, settings: GuildSettings, filesize_limit: int
    ) -> FindFixResult:
        channel_id = message.channel.id

        fix_found = False
        medias: list[Media] = []
        sauces: list[str] = []
        content = ""
        author_md = ""

        channel_is_nsfw = isinstance(message.channel, discord.TextChannel) and message.channel.nsfw
        urls = extract_urls(message.content)

        for url in urls:
            clean_url_ = clean_url(url).replace("www.", "")
            if not any(re.match(pattern, clean_url_) for pattern in FIX_PATTERNS):
                continue

            for domain, fix in FIXES.items():
                if domain in settings.disabled_fixes or domain not in url:
                    continue

                if (
                    domain == "pixiv.net"
                    and not channel_is_nsfw
                    and await self.fetch_info.is_artwork_nsfw(url)
                ):
                    break

                if channel_id in settings.extract_media_channels:
                    result = await self._extract_post_info(
                        domain,
                        url,
                        spoiler=channel_is_nsfw
                        and channel_id not in settings.disable_image_spoilers,
                        filesize_limit=filesize_limit,
                    )
                    medias.extend(
                        Media(url=media.url)
                        if (media.file and get_filesize(media.file.fp) > filesize_limit)
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
                fix_ = "vxreddit.com" if domain == "reddit.com" and settings.use_vxreddit else fix
                message.content = message.content.replace(url, clean_url_.replace(domain, fix_))
                break

        return FindFixResult(
            fix_found=fix_found, medias=medias, sauces=sauces, content=content, author_md=author_md
        )

    async def _extract_post_info(
        self, domain: str, url: str, *, spoiler: bool = False, filesize_limit: int
    ) -> PostExtractionResult:
        media_urls: list[str] = []
        medias: list[Media] = []
        content = ""

        info = None

        if domain == "pixiv.net":
            info = await self.fetch_info.pixiv(url)
            content = info.description if info is not None else ""
            media_urls = info.image_urls if info is not None else []
        elif domain in {"twitter.com", "x.com"}:
            info = await self.fetch_info.twitter(url)
            content = info.content if info is not None else ""
            media_urls = info.media_urls if info is not None else []
        elif domain == "iwara.tv":
            media_urls = await self.fetch_info.iwara(url)
        elif domain == "bsky.app":
            info = await self.fetch_info.bluesky(url)
            content = info.content if info is not None else ""
            media_urls = info.media_urls if info is not None else []
        elif domain == "kemono.su":
            media_urls = await self.fetch_info.kemono(url)

        downloader = MediaDownloader(self.bot.session, media_urls=media_urls)
        await downloader.start(spoiler=spoiler, filesize_limit=filesize_limit)

        for media_url in media_urls:
            file_ = downloader.files.get(media_url)
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
        delete_msg_emoji: str,
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

        # If the message was originally replying to another message, and this message
        # was deleted for a fix, add the reply to the new message.
        if (
            message.reference is not None
            and isinstance(resolved_ref := message.reference.resolved, discord.Message)
            and message.guild is not None
        ):
            if resolved_ref.webhook_id is not None:
                author = await self._get_original_author(resolved_ref, message.guild)
                user = author.mention if author is not None else resolved_ref.author.display_name
            else:
                user = resolved_ref.author.mention

            replying_to = self.bot.translator.get(
                await Translator.get_guild_lang(message.guild),
                "replying_to",
                user=user,
                url=resolved_ref.jump_url,
            )
            message.content = f"{replying_to}\n{message.content}"

        if medias:
            await self._send_files(
                message,
                medias,
                sauces,
                disable_delete_reaction=disable_delete_reaction,
                delete_msg_emoji=delete_msg_emoji,
            )
        else:
            await self._send_message(
                message,
                disable_delete_reaction=disable_delete_reaction,
                delete_msg_emoji=delete_msg_emoji,
            )

    async def _send_files(
        self,
        message: discord.Message,
        medias: list[Media],
        sauces: list[str],
        *,
        delete_msg_emoji: str,
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
                message,
                disable_delete_reaction=disable_delete_reaction,
                delete_msg_emoji=delete_msg_emoji,
                medias=chunk,
                **kwargs,
            )

            message.content = ""

        return fix_message

    async def _send_message(
        self,
        message: discord.Message,
        *,
        disable_delete_reaction: bool,
        delete_msg_emoji: str,
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
            try:
                await fix_message.add_reaction(delete_msg_emoji)
            except discord.HTTPException as e:
                if e.code != 10014:
                    raise
                logger.warning(
                    f"Failed to add {delete_msg_emoji!r} reaction to message {message!r}"
                )

        return fix_message

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
                username=f"{message.author.display_name}{USERNAME_SUFFIX}",
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

    async def _handle_reply(self, message: discord.Message, resolved_ref: discord.Message) -> None:
        guild = message.guild
        if guild is None:
            return

        author = await self._get_original_author(resolved_ref, guild)
        # Can't find author or author is a bot
        if author is None or author.bot:
            return

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
            message, settings=guild_settings, filesize_limit=guild.filesize_limit
        )

        if result.fix_found:
            await self._send_fixes(
                message,
                result,
                disable_delete_reaction=guild_settings.disable_delete_reaction,
                show_post_content=channel.id in guild_settings.show_post_content_channels,
                delete_msg_emoji=guild_settings.delete_msg_emoji,
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
            except discord.NotFound:
                pass

        # If the message is replying to a webhook message, mention the original author
        # of the webhook.
        elif (
            message.reference is not None  # noqa: PLR0916
            and isinstance(resolved_ref := message.reference.resolved, discord.Message)
            and resolved_ref.webhook_id is not None
            and not author.bot
            and not guild_settings.disable_webhook_reply
        ):
            await self._handle_reply(message, resolved_ref)


async def setup(bot: EmbedFixer) -> None:
    await bot.add_cog(FixerCog(bot))
