from __future__ import annotations

import datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from embed_fixer.cogs import fixer as module
from embed_fixer.models import FixedMessage, GuildSettings, ProxyTag, UserSettings
from embed_fixer.settings import FixMode
from tests.support.fixer import fix_result, http_error, make_cog, make_interaction, make_message

if TYPE_CHECKING:
    from typing import Any

pytestmark = pytest.mark.usefixtures("db")


def reaction_payload(*, emoji: str = "❌", user_id: int = 10) -> discord.RawReactionActionEvent:
    payload = discord.RawReactionActionEvent(
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
    payload.member = MagicMock(spec=discord.Member)
    return payload


async def track_message(*, author_id: int = 10, send_type: str = "reply") -> None:
    await FixedMessage.create(
        id=100, guild_id=1, channel_id=2, author_id=author_id, send_type=send_type
    )


@pytest.mark.parametrize("exists", [False, True])
async def test_fixed_message_database_identity_precedes_display_name(exists: bool) -> None:
    message = make_message()
    message.author.display_name = "renamed author"
    cog = make_cog(message)
    if exists:
        await track_message()
        assert await cog._resolve_fixed_message(message) == ("reply", 10)
    else:
        assert await cog._resolve_fixed_message(message) is None


async def test_legacy_fixed_webhook_resolves_exact_display_name() -> None:
    message = make_message()
    message.webhook_id = 77
    message.author.display_name = "discorɗ Alice (Embed Fixer)"
    cog = make_cog(message)
    author = MagicMock(spec=discord.Member)
    author.display_name = "discord Alice"
    author.id = 11
    message.guild.query_members = AsyncMock(return_value=[author])
    assert await cog._resolve_fixed_message(message) == ("webhook", 11)
    message.guild.query_members.assert_awaited_once_with("discord Alice")
    message.guild.query_members.return_value = []
    assert await cog._resolve_fixed_message(message) is None


async def test_legacy_reply_identity_and_dm_guard() -> None:
    message = make_message()
    cog = make_cog(message)
    message.author.id = 99
    original = make_message()
    original.author.id = 12
    message.reference = SimpleNamespace(resolved=original)
    assert await cog._resolve_fixed_message(message) == ("reply", 12)
    message.guild = None
    assert await cog._resolve_fixed_message(message) is None


@pytest.mark.parametrize("cached", [False, True])
async def test_fixed_author_resolves_member_id_before_name(cached: bool) -> None:
    message = make_message()
    cog = make_cog(message)
    await track_message(author_id=12)
    member = MagicMock(spec=discord.Member)
    message.guild.get_member.return_value = member if cached else None
    message.guild.fetch_member = AsyncMock(return_value=member)
    assert await cog._get_fixed_message_author(message, message.guild) is member
    if not cached:
        message.guild.fetch_member.assert_awaited_once_with(12)


async def test_missing_fixed_member_does_not_guess_another_author() -> None:
    message = make_message()
    cog = make_cog(message)
    await track_message()
    message.guild.get_member.return_value = None
    message.guild.fetch_member = AsyncMock(
        side_effect=http_error(status=404, error_type=discord.NotFound)
    )
    assert await cog._get_fixed_message_author(message, message.guild) is None


@pytest.mark.parametrize("webhook", [False, True])
@pytest.mark.parametrize("same_author", [False, True])
async def test_reply_mention_avoids_pinging_self(webhook: bool, same_author: bool) -> None:
    message = make_message()
    reference = make_message()
    reference.webhook_id = 77 if webhook else None
    reference.author.id = 10 if same_author else 11
    reference.author.mention = "<@11>"
    cog = make_cog(message)
    cog._get_fixed_message_author = AsyncMock(return_value=reference.author)
    result = await cog._resolve_author_mention(reference, message)
    assert result == (reference.author.display_name if same_author else "<@11>")
    if webhook:
        cog._get_fixed_message_author.return_value = None
        assert (
            await cog._resolve_author_mention(reference, message) == reference.author.display_name
        )


@pytest.mark.parametrize("mode", list(FixMode))
async def test_message_pipeline_delivers_and_preserves_original_author(mode: FixMode) -> None:
    message = make_message("https://x.com/alice/status/123")
    settings = GuildSettings(id=1, fix_mode=mode)
    await settings.save()
    cog = make_cog(message)
    cog.fetch_info.twitter_is_nsfw = AsyncMock(return_value=False)
    sent = make_message()
    sent.id = 200
    send_type = {
        FixMode.DELETE_AND_RESEND: "webhook",
        FixMode.REPLY: "reply",
        FixMode.RESEND: "resend",
    }[mode]
    cog._send_via_fix_mode = AsyncMock(return_value=(sent, send_type))
    await cog.embed_fixer(message)
    assert message.content == "https://fixupx.com/alice/status/123"
    assert (await FixedMessage.get(id=200)).author_id == 10
    if mode is FixMode.DELETE_AND_RESEND:
        message.delete.assert_awaited_once()
        message.edit.assert_not_awaited()
    else:
        message.delete.assert_not_awaited()
        message.edit.assert_awaited_once_with(suppress=True)


@pytest.mark.parametrize(
    "reason",
    [
        "self",
        "own_webhook",
        "legacy_webhook",
        "dm",
        "ignored",
        "channel",
        "bot",
        "role",
        "proxy",
        "debug",
    ],
)
async def test_message_pipeline_skips_excluded_sources(reason: str) -> None:
    message = make_message("https://x.com/alice/status/123")
    cog = make_cog(message)
    settings = GuildSettings(id=1)
    if reason == "self":
        message.author.id = 99
    elif reason == "own_webhook":
        message.webhook_id = 77
        cog._own_webhook_ids.add(77)
    elif reason == "legacy_webhook":
        message.webhook_id = 77
        message.author.display_name = "Alice (Embed Fixer)"
    elif reason == "dm":
        message.guild = None
    elif reason == "ignored":
        await module.IgnoreMe.add(10)
    elif reason == "channel":
        settings.disable_fix_channels = [2]
    elif reason == "bot":
        message.author.bot = True
    elif reason == "role":
        settings.whitelist_role_ids = [42]
    elif reason == "proxy":
        await UserSettings(id=10, proxy_tags=[ProxyTag(prefix="[", suffix="]")]).save()
        message.content = "[https://x.com/alice/status/123]"
    else:
        message.content = "<@99> jsk py https://x.com/alice/status/123"
    await settings.save()
    cog._find_fixes = AsyncMock()
    await cog.embed_fixer(message)
    cog._find_fixes.assert_not_awaited()
    message.delete.assert_not_awaited()


async def test_visible_proxy_bot_and_allowed_role_are_processed() -> None:
    message = make_message()
    message.author.bot = True
    role = MagicMock(spec=discord.Role)
    role.id = 42
    message.author.roles = [role]
    await GuildSettings(id=1, bot_visibility=True, whitelist_role_ids=[42]).save()
    cog = make_cog(message)
    cog._find_fixes = AsyncMock(return_value=fix_result(found=False))
    await cog.embed_fixer(message)
    cog._find_fixes.assert_awaited_once()
    assert not await cog._is_proxy_trigger(message)


@pytest.mark.parametrize("stage", ["find", "send", "http"])
async def test_message_pipeline_reports_failures_without_deleting_original(
    monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    message = make_message()
    cog = make_cog(message)
    capture = MagicMock()
    monkeypatch.setattr(module, "capture_exception", capture)
    cog._find_fixes = AsyncMock(return_value=fix_result())
    cog._send_fixes = AsyncMock(return_value="webhook")
    if stage == "find":
        cog._find_fixes.side_effect = RuntimeError("failed")
    elif stage == "send":
        cog._send_fixes.side_effect = RuntimeError("failed")
    else:
        cog._send_fixes.side_effect = http_error()
    await cog.embed_fixer(message)
    message.delete.assert_not_awaited()
    assert capture.call_count == (0 if stage == "http" else 1)


async def test_embed_suppression_can_be_disabled() -> None:
    message = make_message()
    cog = make_cog(message)
    await GuildSettings(id=1, disable_embed_suppression=True).save()
    cog._find_fixes = AsyncMock(return_value=fix_result())
    cog._send_fixes = AsyncMock(return_value="reply")
    await cog.embed_fixer(message)
    message.edit.assert_not_awaited()
    message.remove_reaction.assert_awaited_once()


@pytest.mark.parametrize("action", ["delete", "suppress"])
@pytest.mark.parametrize("status", [403, 404])
async def test_original_message_cleanup_tolerates_permission_and_missing_messages(
    action: str, status: int
) -> None:
    message = make_message()
    cog = make_cog(message)
    error = http_error(
        status=status, error_type=discord.Forbidden if status == 403 else discord.NotFound
    )
    if action == "delete":
        message.delete.side_effect = error
        await cog.delete_message_safe(message, message.channel, message.guild)
        assert message.reply.await_count == (1 if status == 403 else 0)
    else:
        message.edit.side_effect = error
        await cog.suppress_embed_safe(message, message.channel, message.guild)


@pytest.mark.parametrize("enabled", [False, True])
async def test_reaction_notifications_require_opt_in_and_use_persisted_identity(
    enabled: bool,
) -> None:
    message = make_message()
    cog = make_cog(message)
    await track_message()
    await UserSettings(id=10, notify_on_react=enabled).save()
    user = MagicMock(spec=discord.User)
    user.send = AsyncMock()
    cast("MagicMock", cog.bot).get_user.return_value = user
    await cog.notify_user_on_react(reaction_payload(user_id=11))
    assert user.send.await_count == int(enabled)
    if enabled:
        assert user.send.await_args is not None
        text = user.send.await_args.args[0]
        assert "<@11>" in text
        assert "https://discord.com/channels/1/2/100" in text


@pytest.mark.parametrize("failure", ["fetch_user", "send_dm"])
async def test_reaction_notification_failure_does_not_escape(failure: str) -> None:
    cog = make_cog()
    await track_message()
    await UserSettings(id=10, notify_on_react=True).save()
    if failure == "fetch_user":
        cast("MagicMock", cog.bot).fetch_user.side_effect = RuntimeError("unavailable")
    else:
        user = MagicMock(spec=discord.User)
        user.send = AsyncMock(side_effect=RuntimeError("closed DMs"))
        cast("MagicMock", cog.bot).get_user.return_value = user
    await cog.notify_user_on_react(reaction_payload(user_id=11))


@pytest.mark.parametrize("authorized", [False, True])
async def test_only_original_author_can_delete_fixed_message(authorized: bool) -> None:
    message = make_message()
    cog = make_cog(message)
    message.channel.fetch_message.return_value = message
    await track_message()
    await cog.manage_reaction_removal(reaction_payload(user_id=10 if authorized else 11))
    assert message.delete.await_count == int(authorized)


async def test_fixed_message_delete_permission_failure_notifies_user() -> None:
    message = make_message()
    cog = make_cog(message)
    message.channel.fetch_message.return_value = message
    message.delete.side_effect = http_error(status=403, error_type=discord.Forbidden)
    await track_message()
    await cog.manage_reaction_removal(reaction_payload())
    message.reply.assert_awaited_once()


@pytest.mark.parametrize(
    "method", ["notify_user_on_react", "manage_reaction_removal", "manage_rotate_fix_reaction"]
)
@pytest.mark.parametrize(
    "reason", ["dm", "self", "wrong_emoji", "missing", "forbidden", "unsupported", "not_fixed"]
)
async def test_reaction_listeners_ignore_irrelevant_or_unavailable_messages(
    method: str, reason: str
) -> None:
    message = make_message()
    cog = make_cog(message)
    payload = reaction_payload(
        emoji="🔄" if method == "manage_rotate_fix_reaction" else "❌", user_id=11
    )
    await GuildSettings(id=1, rotate_fix_reaction=True).save()
    message.channel.fetch_message.return_value = message
    if reason == "dm":
        payload.guild_id = None
    elif reason == "self":
        payload.user_id = 99
    elif reason == "wrong_emoji":
        payload.emoji = discord.PartialEmoji(name="x")
    elif reason == "missing":
        message.channel.fetch_message.side_effect = http_error(
            status=404, error_type=discord.NotFound
        )
    elif reason == "forbidden":
        message.channel.fetch_message.side_effect = http_error(
            status=403, error_type=discord.Forbidden
        )
    elif reason == "unsupported":
        cast("MagicMock", cog.bot).get_channel.return_value = MagicMock(spec=discord.ForumChannel)
    await getattr(cog, method)(payload)
    message.delete.assert_not_awaited()
    message.edit.assert_not_awaited()


@pytest.mark.parametrize("send_type", ["webhook", "reply", "resend"])
async def test_rotation_rewrites_all_same_domain_urls_and_preserves_other_domains(
    send_type: str,
) -> None:
    message = make_message(
        "https://fxtwitter.com/alice/status/123 ||https://fxtwitter.com/bob/status/456|| https://phixiv.net/artworks/7"
    )
    cog = make_cog(message)
    message.channel.fetch_message.return_value = message
    await track_message(send_type=send_type)
    await GuildSettings(id=1, rotate_fix_reaction=True).save()
    webhook = MagicMock(spec=discord.Webhook)
    webhook.edit_message = AsyncMock()
    cog._get_or_create_webhook = AsyncMock(return_value=webhook)
    await cog.manage_rotate_fix_reaction(reaction_payload(emoji="🔄"))
    call = webhook.edit_message.await_args if send_type == "webhook" else message.edit.await_args
    assert call is not None
    content = call.kwargs["content"]
    assert "https://vxtwitter.com/alice/status/123" in content
    assert "||https://vxtwitter.com/bob/status/456||" in content
    assert "https://phixiv.net/artworks/7" in content
    message.remove_reaction.assert_awaited_once()


async def test_unauthorized_rotation_never_edits_message() -> None:
    message = make_message("https://fxtwitter.com/alice/status/123")
    cog = make_cog(message)
    message.channel.fetch_message.return_value = message
    await track_message()
    await GuildSettings(id=1, rotate_fix_reaction=True).save()
    await cog.manage_rotate_fix_reaction(reaction_payload(emoji="🔄", user_id=11))
    message.edit.assert_not_awaited()


async def test_message_deletion_events_and_retention_purge() -> None:
    cog = make_cog()
    for ident in (100, 101, 102, 103):
        await FixedMessage.create(
            id=ident, guild_id=1, channel_id=2, author_id=10, send_type="reply"
        )
    await cog.remove_fixed_message_record(
        discord.RawMessageDeleteEvent({"id": "100", "channel_id": "2", "guild_id": "1"})
    )
    await cog.remove_fixed_message_records(
        discord.RawBulkMessageDeleteEvent(
            {"ids": ["101", "102"], "channel_id": "2", "guild_id": "1"}
        )
    )
    assert await FixedMessage.all().values_list("id", flat=True) == [103]
    await FixedMessage.filter(id=103).update(
        created_at=discord.utils.utcnow() - datetime.timedelta(days=91)
    )
    await cog._purge_fixed_message_records()
    assert await FixedMessage.all().count() == 0


@pytest.mark.parametrize("extract", [False, True])
@pytest.mark.parametrize("nsfw", [False, True])
async def test_context_menu_empty_result_is_ephemeral_after_deferred_response(
    extract: bool, nsfw: bool
) -> None:
    message = make_message()
    cog = make_cog(message)
    interaction = make_interaction(message)
    cog._find_fixes = AsyncMock(return_value=fix_result(found=False, nsfw=nsfw))
    await cog.base_ctx_menu(interaction, message, extract_media=extract)
    interaction.response.defer.assert_awaited_once()
    interaction.delete_original_response.assert_awaited_once()
    assert interaction.followup.send.await_args.kwargs["ephemeral"] is True
    assert cog._find_fixes.await_args is not None
    assert cog._find_fixes.await_args.kwargs["extract_media"] is extract
    assert cog._find_fixes.await_args.kwargs["is_ctx_menu"] is True


@pytest.mark.parametrize("with_guild", [False, True])
async def test_slash_fix_command_rewrites_url_without_touching_original_message(
    with_guild: bool,
) -> None:
    message = make_message(with_guild=with_guild)
    cog = make_cog(message)
    cog.fetch_info.twitter_is_nsfw = AsyncMock(return_value=False)
    interaction = make_interaction(message)
    await cast("Any", cog.fix_url_command.callback)(
        cog, interaction, "https://x.com/alice/status/123"
    )
    interaction.followup.send.assert_awaited_once_with("https://fixupx.com/alice/status/123")
    message.delete.assert_not_awaited()


async def test_context_menu_respects_disabled_channels() -> None:
    message = make_message()
    cog = make_cog(message)
    await GuildSettings(id=1, disable_fix_channels=[2]).save()
    cog._find_fixes = AsyncMock()
    await cog.base_ctx_menu(make_interaction(message), message, extract_media=False)
    cog._find_fixes.assert_not_awaited()
