from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import discord
from aiohttp import ClientResponse

from embed_fixer.cogs.fixer import FindFixResult, FixerCog


def make_message(content: str = "hello", *, with_guild: bool = True) -> MagicMock:
    guild = MagicMock(spec=discord.Guild)
    guild.id = 1
    guild.filesize_limit = 1024
    guild.preferred_locale = discord.Locale.american_english
    guild.me = MagicMock(spec=discord.Member)
    guild.me.id = 99
    channel = MagicMock(spec=discord.TextChannel)
    channel.id = 2
    channel.guild = guild
    channel.nsfw = False
    channel.send = AsyncMock()
    channel.fetch_message = AsyncMock()
    author = MagicMock(spec=discord.Member)
    author.id = 10
    author.bot = False
    author.roles = []
    author.display_name = "Alice"
    author.mention = "<@10>"
    author.display_avatar.url = "https://cdn.example.com/avatar.png"
    message = MagicMock(spec=discord.Message)
    message.id = 100
    message.content = content
    message.guild = guild if with_guild else None
    message.channel = channel
    message.author = author
    message.attachments = []
    message.reference = None
    message.webhook_id = None
    message.tts = False
    message.jump_url = "https://discord.com/channels/1/2/100"
    message.add_reaction = AsyncMock()
    message.remove_reaction = AsyncMock()
    message.reply = AsyncMock()
    message.edit = AsyncMock()
    message.delete = AsyncMock()
    return message


def make_cog(message: MagicMock | None = None) -> FixerCog:
    message = message or make_message()
    bot = MagicMock()
    bot.user.id = 99
    bot.user.mention = "<@99>"
    bot.get_channel.return_value = message.channel
    bot.fetch_channel = AsyncMock(return_value=message.channel)
    bot.get_user.return_value = None
    bot.fetch_user = AsyncMock()
    return FixerCog(bot)


def make_interaction(message: MagicMock | None = None) -> MagicMock:
    message = message or make_message()
    interaction = MagicMock(spec=discord.Interaction)
    interaction.guild = message.guild
    interaction.guild_id = None if message.guild is None else message.guild.id
    interaction.channel = message.channel
    interaction.channel_id = message.channel.id
    interaction.user = message.author
    interaction.response = MagicMock(spec=discord.InteractionResponse)
    interaction.response.is_done.return_value = False
    interaction.response.defer = AsyncMock()
    interaction.response.send_message = AsyncMock()
    interaction.followup = MagicMock()
    interaction.followup.send = AsyncMock()
    interaction.original_response = AsyncMock(return_value=make_message())
    interaction.delete_original_response = AsyncMock()
    return interaction


def http_error(
    *,
    status: int = 400,
    code: int = 0,
    error_type: type[discord.HTTPException] = discord.HTTPException,
) -> discord.HTTPException:
    response = MagicMock(spec=ClientResponse)
    response.status = status
    response.reason = "test failure"
    return error_type(response, {"code": code, "message": "test failure"})


def fix_result(*, found: bool = True, nsfw: bool = False) -> FindFixResult:
    return FindFixResult(
        fix_found=found,
        medias=[],
        sauces=[],
        content="",
        author_md="",
        urls=["https://x.com/alice/status/123"],
        nsfw_skipped=nsfw,
    )
