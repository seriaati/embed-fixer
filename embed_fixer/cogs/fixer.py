from __future__ import annotations

import asyncio
import contextlib
import itertools
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger

from embed_fixer.fixes import DOMAINS, AppendURLFix, Domain, DomainId, FixMethod, Website
from embed_fixer.models import GuildFixMethod, GuildSettings
from embed_fixer.translator import Translator
from embed_fixer.utils.download_media import MediaDownloader
from embed_fixer.utils.fetch_info import PostInfoFetcher
from embed_fixer.utils.misc import (
    append_path_to_url,
    domain_in_url,
    extract_urls,
    get_filesize,
    remove_query_params,
    replace_domain,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from embed_fixer.bot import EmbedFixer, Interaction

USERNAME_SUFFIX: Final[str] = " (Embed Fixer)"


@dataclass(kw_only=True)
class Media:
    url: str
    file: discord.File | None = None


@dataclass(kw_only=True)
class PostExtractionResult:
    medias: list[Media]
    content: str
    author_md: str


@dataclass(kw_only=True)
class FindFixResult:
    fix_found: bool
    medias: list[Media]
    sauces: list[str]
    content: str
    author_md: str
    urls: list[str]


class FixerCog(commands.Cog):
    def __init__(self, bot: EmbedFixer) -> None:
        self.bot = bot
        self.fetch_info = PostInfoFetcher(self.bot.session)
        self.fix_embed_ctx = app_commands.ContextMenu(
            name=app_commands.locale_str("fix_embed"), callback=self.fix_embed
        )
        self.extract_medias_ctx = app_commands.ContextMenu(
            name=app_commands.locale_str("extract_medias"), callback=self.extract_medias
        )

    async def cog_load(self) -> None:
        self.bot.tree.add_command(self.fix_embed_ctx)
        self.bot.tree.add_command(self.extract_medias_ctx)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.fix_embed_ctx.name, type=self.fix_embed_ctx.type)
        self.bot.tree.remove_command(
            self.extract_medias_ctx.name, type=self.extract_medias_ctx.type
        )

    @staticmethod
    def _skip_channel(settings: GuildSettings | None, channel_id: int) -> bool:
        if settings is None:
            return False

        if settings.enable_fix_channels and channel_id not in settings.enable_fix_channels:
            return True

        return channel_id in settings.disable_fix_channels

    async def _nsfw_skip(self, url: str, domain: Domain, *, is_nsfw_channel: bool) -> bool:
        """Skip NSFW domains if the channel is not NSFW."""
        pixiv_skip = (
            domain.id == DomainId.PIXIV
            and not is_nsfw_channel
            and await self.fetch_info.pixiv_is_nsfw(url)
        )
        kemono_skip = domain.id == DomainId.KEMONO and not is_nsfw_channel
        return pixiv_skip or kemono_skip

    @staticmethod
    async def _get_original_author(
        message: discord.Message, guild: discord.Guild
    ) -> discord.Member | None:
        query = message.author.display_name.removesuffix(USERNAME_SUFFIX)
        authors = await guild.query_members(query, limit=100)
        if not authors:
            return None

        return next((a for a in authors if a.display_name == query), None)

    @staticmethod
    async def _determine_fix_method(
        settings: GuildSettings | None, domain: Domain
    ) -> FixMethod | None:
        if not domain.fix_methods:
            return None

        guild_fix_method = (
            None
            if settings is None
            else await GuildFixMethod.get_or_none(guild_id=settings.id, domain_id=domain.id)
        )
        if guild_fix_method is None:
            fix_method = domain.default_fix_method
        else:
            fix_method = next(
                (f for f in domain.fix_methods if f.id == guild_fix_method.fix_id), None
            )
            if fix_method is None:
                logger.warning(
                    f"Fix {guild_fix_method.fix_id} not found for {domain.name} in guild {'Unknown' if settings is None else settings.id}"
                )
                fix_method = domain.default_fix_method

        return fix_method

    @staticmethod
    def _get_matching_domain_website(
        settings: GuildSettings | None, clean_url: str
    ) -> tuple[Domain | None, Website | None]:
        domain: Domain | None = None
        website: Website | None = None

        for d in DOMAINS:
            if settings is not None and d.id in settings.disabled_domains:
                continue

            for w in d.websites:
                if w.match(clean_url):
                    domain = d
                    website = w
                    break

                # Break from outer loop
            else:
                continue
            break
        return domain, website

    @staticmethod
    def _apply_fxembed_translation(url: str, *, translang: str) -> str:
        # FxEmbed (fxtwitter) can translate posts by appending /{lang}
        # See https://github.com/FxEmbed/FxEmbed#translate-posts-xtwitter for more info
        return append_path_to_url(url, f"/{translang}")

    async def _find_fixes(  # noqa: C901, PLR0912, PLR0914, PLR0915
        self,
        message: discord.Message,
        *,
        settings: GuildSettings | None,
        filesize_limit: int | None,
        extract_media: bool = False,
        is_ctx_menu: bool = False,
    ) -> FindFixResult:
        channel_id = message.channel.id

        fix_found = False
        medias: list[Media] = []
        sauces: list[str] = []
        content = ""
        author_md = ""

        is_nsfw_channel = is_ctx_menu or (
            isinstance(message.channel, discord.TextChannel) and message.channel.nsfw
        )
        urls = extract_urls(message.content)

        for url, spoilered in urls:
            clean_url = remove_query_params(url).replace("www.", "")
            domain, website = self._get_matching_domain_website(settings, clean_url)

            if domain is None or website is None:
                continue

            if await self._nsfw_skip(url, domain, is_nsfw_channel=is_nsfw_channel):
                continue

            if extract_media or (
                settings is not None and channel_id in settings.extract_media_channels
            ):
                if not is_ctx_menu:
                    try:
                        asyncio.create_task(message.add_reaction("⏳"))
                    except discord.Forbidden:
                        logger.warning(
                            f"Failed to add reaction to message {message.id} in channel {channel_id}"
                        )

                spoiler = spoilered or (
                    is_nsfw_channel
                    and (settings is not None and channel_id not in settings.disable_image_spoilers)
                )
                result = await self._extract_post_info(
                    domain.id, url, spoiler=spoiler, filesize_limit=filesize_limit
                )
                medias.extend(
                    Media(url=media.url)
                    if (
                        media.file
                        and filesize_limit is not None
                        and get_filesize(media.file.fp) > filesize_limit
                    )
                    else media
                    for media in result.medias
                )
                content, author_md = result.content, result.author_md
                logger.debug(f"Extracted {len(result.medias)} media files from {url}")

                if medias:
                    fix_found = True
                    if spoilered:
                        message.content = message.content.replace(f"||{url}||", "")
                    else:
                        message.content = message.content.replace(url, "")

                    sauces.append(clean_url)
                    continue

            if extract_media:
                continue

            fix_method = await self._determine_fix_method(settings, domain)
            if (
                fix_method is None
                or not fix_method.fixes
                or (website.skip_method_ids and fix_method.id in website.skip_method_ids)
            ):
                continue

            for fix in fix_method.fixes:
                if isinstance(fix, AppendURLFix):
                    new_url = f"https://{fix.domain}?url={clean_url}"
                    if domain.id == DomainId.FACEBOOK:
                        # For facebook, replace /v/ with /r/, found by @zzxc.
                        new_url = new_url.replace("/v/", "/r/")
                else:
                    if not domain_in_url(clean_url, fix.old_domain):
                        continue

                    new_url = replace_domain(clean_url, fix.old_domain, fix.new_domain)

                    if (
                        fix_method.id == 1
                        and settings is not None
                        and settings.translate_target_lang
                    ):  # FxEmbed
                        new_url = self._apply_fxembed_translation(
                            new_url, translang=settings.translate_target_lang
                        )

                if fix_method.has_ads and (
                    settings is not None and not settings.show_original_link_btn
                ):
                    # If the fix method has ads and the guild hasn't enabled
                    # "Show Original Link Button", recommend enabling it.
                    guild_lang = await Translator.get_guild_lang(message.guild)
                    recommend_msg = self.bot.translator.get(
                        guild_lang, "recommend_original_link_btn"
                    )
                    message.content = f"-# {recommend_msg}\n{message.content}"

                fix_found = True
                message.content = message.content.replace(url, new_url)

                break

        return FindFixResult(
            fix_found=fix_found,
            medias=medias,
            sauces=sauces,
            content=content,
            author_md=author_md,
            urls=[url for url, _ in urls],
        )

    async def _extract_post_info(
        self, domain_id: DomainId, url: str, *, spoiler: bool = False, filesize_limit: int | None
    ) -> PostExtractionResult:
        logger.debug(f"Extracting post info from {url} for domain {domain_id!r}")

        media_urls: list[str] = []
        content = ""
        info = None

        try:
            if domain_id is DomainId.PIXIV:
                info = await self.fetch_info.pixiv(url)
                content = "" if info is None else info.description
                media_urls = [] if info is None else info.image_urls
            elif domain_id is DomainId.TWITTER:
                info = await self.fetch_info.twitter(url)
                content = "" if info is None else info.text
                media_urls = [] if info is None else [media.url for media in info.medias]
            elif domain_id is DomainId.BLUESKY:
                info = await self.fetch_info.bluesky(url)
                content = "" if info is None else info.record.text
                media_urls = [] if info is None else info.media_urls
            elif domain_id is DomainId.KEMONO:
                media_urls = await self.fetch_info.kemono(url)
        except Exception:
            logger.exception(f"Failed to extract post info from {url} for domain {domain_id!r}")
            return PostExtractionResult(medias=[], content="", author_md="")

        logger.debug(f"Extracted media URLs: {media_urls}")

        downloader = MediaDownloader(self.bot.session, media_urls=media_urls)
        await downloader.start(spoiler=spoiler, filesize_limit=filesize_limit)

        medias: list[Media] = []

        for media_url in media_urls:
            file_ = downloader.files.get(media_url)
            medias.append(Media(url=media_url, file=file_))

        logger.debug(f"Downloaded {len(medias)} media files")

        return PostExtractionResult(
            medias=medias, content=content[:2000], author_md="" if info is None else info.author_md
        )

    async def _resolve_author_mention(
        self, resolved_ref: discord.Message, message: discord.Message
    ) -> str:
        assert message.guild is not None

        # Replying to a webhook message
        if resolved_ref.webhook_id is not None:
            author = await self._get_original_author(resolved_ref, message.guild)

            if author is None:
                return resolved_ref.author.display_name

            # Author of the webhook message is the same as this message's author, don't mention
            if author.id == message.author.id:
                return author.display_name

            return author.mention

        # Replying to a normal message
        if resolved_ref.author.id == message.author.id:
            # Author of the normal message is the same as this message's author, don't mention
            return resolved_ref.author.display_name

        return resolved_ref.author.mention

    async def _send_fixes(
        self,
        message: discord.Message,
        result: FindFixResult,
        *,
        guild_settings: GuildSettings | None,
        interaction: Interaction | None = None,
    ) -> None:
        silent = False
        medias, sauces = result.medias, result.sauces
        medias.extend([Media(url=a.url, file=await a.to_file()) for a in message.attachments])

        show_post_content = (
            None
            if guild_settings is None
            else message.channel.id in guild_settings.show_post_content_channels
        )

        if show_post_content:
            if result.author_md:
                message.content += f"\n-# {result.author_md}"
            if result.content:
                message.content += f"\n{result.content}"

        if len(sauces) > 1:
            sauces_str = "\n".join(f"<{sauce}>" for sauce in sauces)
            message.content += f"\n||{sauces_str}||"
            sauces.clear()

        # If the message was originally replying to another message, since this message
        # will be deleted for a fix, add the reply to the new message containing the fix.
        if (
            message.reference is not None
            and isinstance(resolved_ref := message.reference.resolved, discord.Message)
            and message.guild is not None
        ):
            mention = await self._resolve_author_mention(resolved_ref, message)

            replying_to = self.bot.translator.get(
                await Translator.get_guild_lang(message.guild),
                "replying_to",
                user=mention,
                url=resolved_ref.jump_url,
            )
            message.content = f"{replying_to}\n{message.content}"
            silent = True

        if medias:
            await self._send_files(
                message,
                medias,
                sauces,
                guild_settings=guild_settings,
                interaction=interaction,
                silent=silent,
            )
        else:
            await self._send_message(
                message,
                urls=result.urls,
                guild_settings=guild_settings,
                interaction=interaction,
                silent=silent,
            )

    async def _send_files(  # noqa: PLR0913
        self,
        message: discord.Message,
        medias: list[Media],
        sauces: list[str],
        *,
        guild_settings: GuildSettings | None,
        interaction: Interaction | None = None,
        silent: bool = False,
    ) -> None:
        """Send multiple files in batches of 10."""
        guild_lang: str | None = None

        for chunk in itertools.batched(medias, 10):
            kwargs: dict[str, Any] = {"silent": silent}
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

            await self._send_message(
                message,
                guild_settings=guild_settings,
                medias=chunk,
                interaction=interaction,
                **kwargs,
            )

            message.content = ""

    async def _send_message(
        self,
        message: discord.Message,
        *,
        urls: list[str] | None = None,
        guild_settings: GuildSettings | None,
        medias: Sequence[Media] | None = None,
        interaction: Interaction | None = None,
        **kwargs: Any,
    ) -> None:
        """Send a message with a webhook, interaction, or regular message."""
        fix_message: discord.Message | None = None

        medias = medias or []
        files = [media.file for media in medias if media.file is not None]

        # Settings
        disable_delete_reaction = (
            None if guild_settings is None else guild_settings.disable_delete_reaction
        )
        delete_msg_emoji = None if guild_settings is None else guild_settings.delete_msg_emoji
        funnel_target_channel = (
            None if guild_settings is None else guild_settings.funnel_target_channel
        )
        show_original_link_btn = (
            False if guild_settings is None else guild_settings.show_original_link_btn
        )

        if show_original_link_btn and urls:
            guild_lang = await Translator.get_guild_lang(message.guild)
            view = discord.ui.View()
            view.add_item(
                discord.ui.Button(
                    url=urls[0], label=self.bot.translator.get(guild_lang, "original_link")
                )
            )
            kwargs["view"] = view

        if interaction is not None:
            allowed_mentions = discord.AllowedMentions(
                everyone=False, users=False, roles=False, replied_user=False
            )

            if interaction.response.is_done():
                await interaction.followup.send(
                    message.content,
                    tts=message.tts,
                    files=files,
                    allowed_mentions=allowed_mentions,
                    **kwargs,
                )
            else:
                await interaction.response.send_message(
                    message.content,
                    tts=message.tts,
                    files=files,
                    allowed_mentions=allowed_mentions,
                    **kwargs,
                )

            fix_message = await interaction.original_response()
        else:
            webhook_channel = message.channel

            if funnel_target_channel is not None:
                target_channel = self.bot.get_channel(
                    funnel_target_channel
                ) or await self.bot.fetch_channel(funnel_target_channel)

                webhook_channel = target_channel

            webhook = await self._get_or_create_webhook(webhook_channel, message.guild)

            try:
                if webhook is not None:
                    try:
                        fix_message = await self._send_webhook(
                            message, webhook, files=files, **kwargs
                        )
                    except discord.HTTPException as e:
                        err_message = self.bot.translator.get(
                            await Translator.get_guild_lang(message.guild), "failed_to_send_webhook"
                        )
                        await message.channel.send(f"{err_message}\n\n{e}")
                else:
                    fix_message = await message.channel.send(
                        message.content, tts=message.tts, files=files, **kwargs
                    )
            except discord.HTTPException as e:
                if e.code != 40005:  # Request entity too large
                    raise

                message.content += "\n".join(media.url for media in medias)
                await self._send_message(message, guild_settings=guild_settings, **kwargs)

        await self._add_delete_reaction(
            message, interaction, fix_message, disable_delete_reaction, delete_msg_emoji
        )

    async def _add_delete_reaction(
        self,
        message: discord.Message,
        interaction: Interaction | None,
        fix_message: discord.Message | None,
        disable_delete_reaction: bool | None,
        delete_msg_emoji: str | None,
    ) -> None:
        if (
            not disable_delete_reaction
            and delete_msg_emoji
            and interaction is None
            and fix_message is not None
        ):
            guild_id = message.guild.id if message.guild else "DM"
            err_message = f"Failed to add reaction {delete_msg_emoji!r} to message {fix_message.id} in {guild_id}"

            try:
                await fix_message.add_reaction(delete_msg_emoji)
            except discord.Forbidden:
                logger.warning(err_message)
                with contextlib.suppress(discord.Forbidden):
                    await fix_message.reply(
                        self.bot.translator.get(
                            await Translator.get_guild_lang(message.guild),
                            "no_perms_to_add_reactions",
                        )
                    )
            except discord.HTTPException:
                logger.error(err_message)
                with contextlib.suppress(discord.Forbidden):
                    await fix_message.reply(
                        self.bot.translator.get(
                            await Translator.get_guild_lang(message.guild),
                            "add_reaction_error",
                            emoji=delete_msg_emoji,
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

    async def _get_or_create_webhook(
        self,
        channel: discord.abc.GuildChannel
        | discord.abc.MessageableChannel
        | discord.abc.PrivateChannel,
        guild: discord.Guild | None,
    ) -> discord.Webhook | None:
        if not isinstance(channel, discord.TextChannel):
            return None

        try:
            webhooks = await channel.webhooks()
        except discord.Forbidden:
            with contextlib.suppress(discord.Forbidden):
                await channel.send(
                    self.bot.translator.get(
                        await Translator.get_guild_lang(guild), "no_perms_to_manage_webhooks"
                    )
                )
            return None

        webhook_name = self.bot.user.name
        webhook = discord.utils.get(webhooks, name=webhook_name)
        if webhook is None:
            webhook = await channel.create_webhook(
                name=webhook_name, avatar=await self.bot.user.display_avatar.read()
            )

        return webhook

    async def _handle_reply(self, message: discord.Message, resolved_ref: discord.Message) -> None:
        guild = message.guild
        if guild is None:
            return

        author = await self._get_original_author(resolved_ref, guild)
        # Can't find author or author is a bot or the author is the same as the message author
        if author is None or author.bot or author.id == message.author.id:
            return

        await message.reply(
            self.bot.translator.get(
                await Translator.get_guild_lang(guild),
                "replying_to",
                user=author.mention,
                url=resolved_ref.jump_url,
            ),
            mention_author=False,
            silent=True,
        )

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        if payload.guild_id is None or payload.user_id == self.bot.user.id:
            return

        settings, _ = await GuildSettings.get_or_create(id=payload.guild_id)
        if str(payload.emoji) != settings.delete_msg_emoji:
            return

        channel_id = payload.channel_id
        channel = self.bot.get_channel(channel_id) or await self.bot.fetch_channel(channel_id)
        if isinstance(
            channel, discord.ForumChannel | discord.CategoryChannel | discord.abc.PrivateChannel
        ):
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.Forbidden:
            logger.warning(
                f"Failed to fetch message in {channel!r}, bot perms: {channel.permissions_for(channel.guild.me)}"
            )
            return

        if USERNAME_SUFFIX not in message.author.display_name or (guild := message.guild) is None:
            return

        author = await self._get_original_author(message, guild)
        if author is None:
            return

        if payload.user_id == author.id:
            try:
                await message.delete()
            except discord.Forbidden:
                logger.warning(f"Failed to delete message in {channel.id=} in {guild.id=}")
                with contextlib.suppress(discord.Forbidden):
                    await message.reply(
                        self.bot.translator.get(
                            await Translator.get_guild_lang(guild), "no_perms_to_delete_msg"
                        )
                    )

    @commands.Cog.listener("on_message")
    async def embed_fixer(self, message: discord.Message) -> None:
        if message.content.startswith(f"{self.bot.user.mention} jsk py"):
            return

        channel, guild, author = message.channel, message.guild, message.author

        if (
            (message.webhook_id is not None and USERNAME_SUFFIX in author.display_name)
            or self.bot.user.id == author.id
            or guild is None
        ):
            return

        guild_settings, _ = await GuildSettings.get_or_create(id=guild.id)
        whitelist_role_skip = (
            isinstance(author, discord.Member)
            and guild_settings.whitelist_role_ids
            and not any(role.id in guild_settings.whitelist_role_ids for role in author.roles)
        )
        if (
            self._skip_channel(guild_settings, channel.id)
            or (not guild_settings.bot_visibility and author.bot)
            or whitelist_role_skip
        ):
            return

        result = await self._find_fixes(
            message, settings=guild_settings, filesize_limit=guild.filesize_limit
        )

        if result.fix_found:
            try:
                await self._send_fixes(message, result, guild_settings=guild_settings)
            except discord.Forbidden:
                logger.warning(f"Failed to send fixes in {channel.id=} in {guild.id=}")

            try:
                await message.delete()
            except discord.Forbidden:
                logger.warning(f"Failed to delete message in {channel.id=} in {guild.id=}")
                with contextlib.suppress(discord.Forbidden):
                    await message.reply(
                        self.bot.translator.get(
                            await Translator.get_guild_lang(guild), "no_perms_to_delete_msg"
                        )
                    )
            except discord.NotFound:
                pass

        # If this is a normal message (no embed fix found) replying to a webhook message,
        # reply to this message containing mention to the original author of the webhook message.
        elif (
            message.reference is not None
            and isinstance(resolved_ref := message.reference.resolved, discord.Message)
            and resolved_ref.webhook_id is not None
            and not author.bot
            and not guild_settings.disable_webhook_reply
        ):
            await self._handle_reply(message, resolved_ref)

    async def base_ctx_menu(
        self, i: Interaction, message: discord.Message, *, extract_media: bool
    ) -> None:
        await i.response.defer()

        if i.guild_id is not None:
            guild_settings = await GuildSettings.get_or_none(id=i.guild_id)
        else:
            guild_settings = None

        if i.channel_id is not None and self._skip_channel(guild_settings, i.channel_id):
            return

        result = await self._find_fixes(
            message,
            settings=guild_settings,
            filesize_limit=None if i.guild is None else i.guild.filesize_limit,
            extract_media=extract_media,
            is_ctx_menu=True,
        )

        if result.fix_found:
            try:
                await self._send_fixes(
                    message, result, guild_settings=guild_settings, interaction=i
                )
            except discord.Forbidden:
                logger.warning(f"Failed to send fixes in {i.channel_id=} in {i.guild_id=}")
        else:
            await i.followup.send(
                self.bot.translator.get(
                    await Translator.get_guild_lang(i.guild), "no_fixes_found", url=message.jump_url
                )
            )

    async def fix_embed(self, i: Interaction, message: discord.Message) -> None:
        await self.base_ctx_menu(i, message, extract_media=False)

    async def extract_medias(self, i: Interaction, message: discord.Message) -> None:
        await self.base_ctx_menu(i, message, extract_media=True)


async def setup(bot: EmbedFixer) -> None:
    await bot.add_cog(FixerCog(bot))
