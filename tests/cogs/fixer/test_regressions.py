from __future__ import annotations

from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from embed_fixer.cogs.fixer import Media
from embed_fixer.models import FixedMessage, GuildSettings, GuildSettingsTable, UserSettingsTable
from embed_fixer.settings import FixMode
from tests.support.fixer import fix_result, http_error, make_cog, make_interaction, make_message

pytestmark = pytest.mark.usefixtures("db")


def make_reaction(*, user_id: int = 10, emoji: str = "🔄") -> discord.RawReactionActionEvent:
    event = discord.RawReactionActionEvent(
        {
            "guild_id": "1",
            "channel_id": "2",
            "message_id": "100",
            "user_id": str(user_id),
            "message_author_id": "99",
            "emoji": {"name": emoji, "id": None, "animated": False},
            "burst": False,
            "type": 0,
        },
        discord.PartialEmoji(name=emoji),
        "REACTION_ADD",
    )
    event.member = MagicMock(spec=discord.Member)
    return event


@pytest.mark.parametrize("already_responded", [False, True])
async def test_interaction_media_batches_track_each_distinct_delivered_message(
    *, already_responded: bool
) -> None:
    message = make_message("caption")
    cog = make_cog(message)
    interaction = make_interaction(message)
    interaction.response.is_done.return_value = already_responded
    first = make_message()
    first.id = 200
    second = make_message()
    second.id = 201
    interaction.original_response.return_value = first
    interaction.followup.send.side_effect = [first, second] if already_responded else [second]

    def mark_responded(*_args: object, **_kwargs: object) -> None:
        interaction.response.is_done.return_value = True

    interaction.response.send_message.side_effect = mark_responded

    result = await cog._send_files(
        message,
        [Media(url=f"https://cdn.test/{index}") for index in range(11)],
        [],
        guild_settings=GuildSettings(id=1),
        filesize_limit=1024,
        interaction=interaction,
    )

    assert result == "interaction"
    assert interaction.followup.send.await_count == (2 if already_responded else 1)
    assert interaction.original_response.await_count == (0 if already_responded else 1)
    assert all(call.kwargs["wait"] for call in interaction.followup.send.await_args_list)
    assert await FixedMessage.all().order_by("id").values_list("id", flat=True) == [200, 201]
    assert await FixedMessage.all().values_list("author_id", flat=True) == [10, 10]
    sends = [
        *interaction.response.send_message.await_args_list,
        *interaction.followup.send.await_args_list,
    ]
    first_content, second_content = [entry.args[0] for entry in sends]
    assert first_content.startswith("caption\n")
    assert "https://cdn.test/9" in first_content
    assert second_content == "\nhttps://cdn.test/10"


async def test_send_fixes_retains_reply_reference_and_author_mention() -> None:
    message = make_message("caption")
    reference = make_message()
    reference.id = 50
    reference.author.id = 11
    reference.author.mention = "<@11>"
    reference.jump_url = "https://discord.com/channels/1/2/50"
    message.reference = SimpleNamespace(resolved=reference)
    sent = make_message()
    sent.id = 200
    message.reply.return_value = sent
    cog = make_cog(message)

    result = await cog._send_fixes(
        message,
        fix_result(),
        guild_settings=GuildSettings(
            id=1, fix_mode=FixMode.REPLY, disable_delete_reaction=True, show_original_link_btn=False
        ),
        filesize_limit=1024,
    )

    assert result == "reply"
    message.reply.assert_awaited_once_with(
        "⬅️ Replying to <@11> (https://discord.com/channels/1/2/50)\ncaption",
        tts=False,
        files=[],
        mention_author=False,
    )
    assert (await FixedMessage.get(id=200)).author_id == 10


@pytest.mark.parametrize("exact_match", [False, True])
async def test_untracked_fixed_author_requires_exact_legacy_display_name(
    *, exact_match: bool
) -> None:
    message = make_message()
    message.author.display_name = "discorɗ Alice (Embed Fixer)"
    cog = make_cog(message)
    partial = MagicMock(spec=discord.Member)
    partial.display_name = "discord Alice Two"
    exact = MagicMock(spec=discord.Member)
    exact.display_name = "discord Alice"
    message.guild.query_members = AsyncMock(
        return_value=[partial, exact] if exact_match else [partial]
    )

    result = await cog._get_fixed_message_author(message, message.guild)

    assert result is (exact if exact_match else None)
    message.guild.query_members.assert_awaited_once_with("discord Alice")
    message.guild.get_member.assert_not_called()
    assert await FixedMessage.all().count() == 0


@pytest.mark.parametrize("send_type", ["webhook", "reply"])
@pytest.mark.parametrize("status", [403, 500])
async def test_failed_rotation_edits_keep_reaction_and_preserve_tracked_identity(
    send_type: str, status: int
) -> None:
    message = make_message("https://fxtwitter.com/alice/status/123")
    message.channel.fetch_message.return_value = message
    cog = make_cog(message)
    await GuildSettings(id=1, rotate_fix_reaction=True).save()
    await FixedMessage.create(id=100, guild_id=1, channel_id=2, author_id=10, send_type=send_type)
    error = http_error(
        status=status, error_type=discord.Forbidden if status == 403 else discord.HTTPException
    )
    webhook = MagicMock(spec=discord.Webhook)
    webhook.name = cog.bot.user.name
    webhook.id = 77
    webhook.edit_message = AsyncMock(side_effect=error)
    message.channel.webhooks = AsyncMock(return_value=[webhook])
    message.edit.side_effect = error

    await cog.manage_rotate_fix_reaction(make_reaction())

    if send_type == "webhook":
        assert webhook.edit_message.await_args is not None
        assert webhook.edit_message.await_args.args == (100,)
        assert (
            webhook.edit_message.await_args.kwargs["content"]
            == "https://vxtwitter.com/alice/status/123"
        )
        message.edit.assert_not_awaited()
    else:
        assert message.edit.await_args is not None
        assert message.edit.await_args.kwargs["content"] == "https://vxtwitter.com/alice/status/123"
        webhook.edit_message.assert_not_awaited()
    message.remove_reaction.assert_not_awaited()
    assert message.content == "https://fxtwitter.com/alice/status/123"
    assert (await FixedMessage.get(id=100)).author_id == 10


async def test_rotation_without_webhook_permissions_keeps_message_and_reaction() -> None:
    message = make_message("https://fxtwitter.com/alice/status/123")
    message.channel.fetch_message.return_value = message
    message.channel.webhooks = AsyncMock(
        side_effect=http_error(status=403, error_type=discord.Forbidden)
    )
    message.channel.create_webhook = AsyncMock()
    cog = make_cog(message)
    await GuildSettings(id=1, rotate_fix_reaction=True).save()
    await FixedMessage.create(id=100, guild_id=1, channel_id=2, author_id=10, send_type="webhook")

    await cog.manage_rotate_fix_reaction(make_reaction())

    message.channel.webhooks.assert_awaited_once()
    message.channel.send.assert_awaited_once()
    message.channel.create_webhook.assert_not_awaited()
    message.edit.assert_not_awaited()
    message.remove_reaction.assert_not_awaited()
    assert message.content == "https://fxtwitter.com/alice/status/123"


@pytest.mark.parametrize(
    "reason", ["foreign_message_author", "unresolved_message", "self_reaction"]
)
async def test_legacy_notifications_skip_unrecognized_messages_and_self_reactions(
    reason: str,
) -> None:
    message = make_message()
    message.channel.fetch_message.return_value = message
    cog = make_cog(message)
    bot = cast("MagicMock", cog.bot)
    payload = make_reaction(emoji="😀")
    if reason == "foreign_message_author":
        payload.message_author_id = 88
    elif reason == "self_reaction":
        payload.message_author_id = None
        message.webhook_id = 77
        message.author.display_name = "Alice (Embed Fixer)"
        original_author = MagicMock(spec=discord.Member)
        original_author.id = payload.user_id
        original_author.display_name = "Alice"
        message.guild.query_members = AsyncMock(return_value=[original_author])

    await cog.notify_user_on_react(payload)

    bot.get_user.assert_not_called()
    bot.fetch_user.assert_not_awaited()
    if reason == "foreign_message_author":
        message.channel.fetch_message.assert_not_awaited()
    else:
        message.channel.fetch_message.assert_awaited_once_with(100)
    if reason == "self_reaction":
        message.guild.query_members.assert_awaited_once_with("Alice")
    assert await UserSettingsTable.all().count() == 0


@pytest.mark.parametrize("has_fix", [False, True])
async def test_context_menu_in_dm_uses_no_guild_settings(
    *, has_fix: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    message = make_message(
        "https://x.com/alice/status/123" if has_fix else "plain text", with_guild=False
    )
    message.channel = MagicMock(spec=discord.DMChannel)
    message.channel.id = 2
    cog = make_cog(message)
    interaction = make_interaction(message)
    interaction.response.is_done.return_value = True
    guild_settings_query = AsyncMock(wraps=GuildSettings.get_or_none)
    monkeypatch.setattr(GuildSettings, "get_or_none", guild_settings_query)

    await cog.base_ctx_menu(interaction, message, extract_media=False)

    interaction.response.defer.assert_awaited_once()
    guild_settings_query.assert_not_awaited()
    assert await GuildSettingsTable.all().count() == 0
    assert await FixedMessage.all().count() == 0
    if has_fix:
        assert interaction.followup.send.await_args is not None
        assert interaction.followup.send.await_args.args == ("https://fixupx.com/alice/status/123",)
        interaction.delete_original_response.assert_not_awaited()
    else:
        interaction.delete_original_response.assert_awaited_once()
        assert interaction.followup.send.await_args is not None
        assert interaction.followup.send.await_args.kwargs["ephemeral"] is True
