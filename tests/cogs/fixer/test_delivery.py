from __future__ import annotations

import asyncio
import io
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from embed_fixer.cogs import fixer as module
from embed_fixer.cogs.fixer import FixerCog, Media, add_reaction_safe, remove_reaction_safe
from embed_fixer.models import FixedMessage, GuildSettings, UserSettings
from embed_fixer.settings import FixMode
from tests.support.fixer import fix_result, http_error, make_cog, make_interaction, make_message

if TYPE_CHECKING:
    from collections.abc import Coroutine


def make_media(size: int, index: int = 0) -> Media:
    return Media(
        url=f"https://cdn.test/{index}.png",
        file=discord.File(io.BytesIO(b"x" * size), filename=f"{index}.png"),
    )


@pytest.mark.parametrize(
    ("sizes", "limit", "expected"),
    [
        ([], 10, []),
        ([4, 6], 10, [2]),
        ([4, 7, 3], 10, [1, 2]),
        ([1] * 11, 100, [10, 1]),
        ([12, 1], 10, [1, 1]),
    ],
)
def test_media_batches_respect_size_count_and_order(
    sizes: list[int], limit: int, expected: list[int]
) -> None:
    medias = [make_media(size, index) for index, size in enumerate(sizes)]
    batches = FixerCog._batch_medias(medias, limit)
    assert [len(batch) for batch in batches] == expected
    assert [media.url for batch in batches for media in batch] == [media.url for media in medias]


def test_url_fallbacks_do_not_consume_file_size_budget() -> None:
    medias = [make_media(10), Media(url="https://cdn.test/fallback")]
    assert FixerCog._batch_medias(medias, 10) == [medias]


@pytest.mark.parametrize("done", [False, True])
async def test_interaction_delivery_disables_all_mentions(done: bool) -> None:
    message = make_message("@everyone fixed")
    cog = make_cog(message)
    interaction = make_interaction(message)
    interaction.response.is_done.return_value = done
    file = make_media(1).file
    assert file is not None
    result = await cog._send_via_interaction(interaction, message, [file])
    sender = interaction.followup.send if done else interaction.response.send_message
    sender.assert_awaited_once()
    assert sender.await_args.args == (message.content,)
    assert sender.await_args.kwargs["files"] == [file]
    assert sender.await_args.kwargs["allowed_mentions"].to_dict() == {"parse": []}
    if done:
        assert sender.await_args.kwargs["wait"] is True
        assert result is interaction.followup.send.return_value
        interaction.original_response.assert_not_awaited()
    else:
        assert result is interaction.original_response.return_value
        interaction.original_response.assert_awaited_once()


@pytest.mark.parametrize("cached", [False, True])
async def test_funnel_channel_resolves_cache_then_api(cached: bool) -> None:
    message = make_message()
    cog = make_cog(message)
    target = MagicMock(spec=discord.TextChannel)
    bot = cast("MagicMock", cog.bot)
    bot.get_channel.return_value = target if cached else None
    bot.fetch_channel.return_value = target
    assert await cog._get_target_channel(message, None) is message.channel
    assert await cog._get_target_channel(message, 123) is target
    if cached:
        bot.fetch_channel.assert_not_awaited()
    else:
        bot.fetch_channel.assert_awaited_once_with(123)


@pytest.mark.parametrize("mode", list(FixMode))
async def test_fix_mode_selects_webhook_reply_or_resend(mode: FixMode) -> None:
    message = make_message("fixed")
    cog = make_cog(message)
    webhook = MagicMock(spec=discord.Webhook)
    cog._get_or_create_webhook = AsyncMock(return_value=webhook)
    cog._send_webhook = AsyncMock(return_value=make_message())
    result, send_type = await cog._send_via_fix_mode(message, message.channel, [], fix_mode=mode)
    assert result is not None
    if mode is FixMode.DELETE_AND_RESEND:
        assert send_type == "webhook"
        cog._send_webhook.assert_awaited_once()
        message.reply.assert_not_awaited()
    elif mode is FixMode.REPLY:
        assert send_type == "reply"
        assert message.reply.await_args.kwargs["mention_author"] is False
    else:
        assert send_type == "resend"
        message.channel.send.assert_awaited_once_with("fixed", tts=False, files=[])


async def test_unavailable_webhook_falls_back_to_reply() -> None:
    message = make_message()
    cog = make_cog(message)
    cog._get_or_create_webhook = AsyncMock(return_value=None)
    _, send_type = await cog._send_via_fix_mode(message, message.channel, [])
    assert send_type == "reply"
    message.reply.assert_awaited_once()


@pytest.mark.usefixtures("db")
async def test_webhook_error_is_visible_and_reraised() -> None:
    message = make_message()
    cog = make_cog(message)
    cog._get_or_create_webhook = AsyncMock(return_value=MagicMock())
    cog._send_webhook = AsyncMock(side_effect=RuntimeError("send failure"))
    with pytest.raises(RuntimeError, match="send failure"):
        await cog._send_via_fix_mode(message, message.channel, [])
    assert "send failure" in message.channel.send.await_args.args[0]
    assert message.channel.send.await_args.kwargs["delete_after"] == 10


@pytest.mark.parametrize("hide_suffix", [False, True])
async def test_webhook_payload_sanitizes_name_and_preserves_identity(hide_suffix: bool) -> None:
    message = make_message()
    message.author.display_name = "Discord Alice"
    cog = make_cog(message)
    webhook = MagicMock(spec=discord.Webhook)
    webhook.send = AsyncMock()
    await cog._send_webhook(message, webhook, hide_username_suffix=hide_suffix)
    assert webhook.send.await_args is not None
    payload = webhook.send.await_args.kwargs
    assert payload["username"] == "discorɗ Alice" + ("" if hide_suffix else " (Embed Fixer)")
    assert payload["avatar_url"] == message.author.display_avatar.url
    assert payload["wait"] is True
    assert payload["silent"] is True
    assert payload["thread"] is discord.utils.MISSING


@pytest.mark.parametrize("existing", [False, True])
async def test_webhook_lookup_registers_own_ids_before_send(existing: bool) -> None:
    message = make_message()
    cog = make_cog(message)
    webhook = MagicMock(spec=discord.Webhook)
    webhook.id = 1234
    webhook.name = cog.bot.user.name
    message.channel.webhooks = AsyncMock(return_value=[webhook] if existing else [])
    message.channel.create_webhook = AsyncMock(return_value=webhook)
    bot = cast("MagicMock", cog.bot)
    bot.user.display_avatar.read = AsyncMock(return_value=b"avatar")
    assert await cog._get_or_create_webhook(message.channel, message.guild) is webhook
    assert webhook.id in cog._own_webhook_ids
    if existing:
        message.channel.create_webhook.assert_not_awaited()
    else:
        message.channel.create_webhook.assert_awaited_once_with(
            name=cog.bot.user.name, avatar=b"avatar"
        )


async def test_thread_posts_via_parent_webhook() -> None:
    message = make_message()
    thread = MagicMock(spec=discord.Thread)
    thread.parent = message.channel
    cog = make_cog(message)
    webhook = MagicMock(spec=discord.Webhook)
    webhook.id = 123
    webhook.name = cog.bot.user.name
    message.channel.webhooks = AsyncMock(return_value=[webhook])
    assert await cog._get_or_create_webhook(thread, message.guild) is webhook
    cog._get_or_create_webhook = AsyncMock(return_value=webhook)
    cog._send_webhook = AsyncMock()
    await cog._send_via_fix_mode(message, thread, [])
    assert cog._send_webhook.await_args is not None
    assert cog._send_webhook.await_args.kwargs["thread"] is thread


@pytest.mark.usefixtures("db")
async def test_webhook_permission_failure_reports_problem_and_allows_fallback() -> None:
    message = make_message()
    cog = make_cog(message)
    message.channel.webhooks = AsyncMock(
        side_effect=http_error(status=403, error_type=discord.Forbidden)
    )
    assert await cog._get_or_create_webhook(message.channel, message.guild) is None
    message.channel.send.assert_awaited_once()
    assert await cog._get_or_create_webhook(MagicMock(spec=discord.DMChannel), None) is None


@pytest.mark.usefixtures("db")
@pytest.mark.parametrize("user_mode", [None, *list(FixMode)])
async def test_delivery_uses_user_preference_and_persists_original_author(
    user_mode: FixMode | None,
) -> None:
    message = make_message()
    cog = make_cog(message)
    await UserSettings(id=10, fix_mode=user_mode).save()
    sent = make_message()
    sent.id = 200
    cog._send_via_fix_mode = AsyncMock(return_value=(sent, "reply"))
    cog._add_delete_reaction = AsyncMock()
    settings = GuildSettings(id=1, fix_mode=FixMode.RESEND)
    assert await cog._send_message(message, guild_settings=settings) == "reply"
    assert cog._send_via_fix_mode.await_args is not None
    assert cog._send_via_fix_mode.await_args.kwargs["fix_mode"] is (user_mode or FixMode.RESEND)
    record = await FixedMessage.get(id=200)
    assert (record.author_id, record.guild_id, record.channel_id, record.send_type) == (
        10,
        1,
        2,
        "reply",
    )


@pytest.mark.usefixtures("db")
async def test_interaction_delivery_and_original_link_button() -> None:
    message = make_message()
    cog = make_cog(message)
    sent = make_message()
    sent.id = 200
    cog._send_via_interaction = AsyncMock(return_value=sent)
    cog._add_delete_reaction = AsyncMock()
    result = await cog._send_message(
        message,
        guild_settings=GuildSettings(id=1),
        urls=["https://original.test/a"],
        interaction=make_interaction(message),
    )
    assert result == "interaction"
    assert cog._send_via_interaction.await_args is not None
    view = cog._send_via_interaction.await_args.kwargs["view"]
    assert view.children[0].url == "https://original.test/a"
    assert (await FixedMessage.get(id=200)).send_type == "interaction"


@pytest.mark.usefixtures("db")
@pytest.mark.parametrize("unlocked", [False, True])
async def test_hidden_webhook_suffix_requires_sponsorship(
    monkeypatch: pytest.MonkeyPatch, unlocked: bool
) -> None:
    message = make_message()
    cog = make_cog(message)
    cog._send_via_fix_mode = AsyncMock(return_value=(None, "webhook"))
    cog._add_delete_reaction = AsyncMock()
    monkeypatch.setattr(module.sponsors, "is_guild_unlocked", AsyncMock(return_value=unlocked))
    await cog._send_message(message, guild_settings=GuildSettings(id=1, hide_webhook_suffix=True))
    assert cog._send_via_fix_mode.await_args is not None
    assert cog._send_via_fix_mode.await_args.kwargs["hide_username_suffix"] is unlocked


@pytest.mark.usefixtures("db")
async def test_large_upload_retries_as_urls_without_files() -> None:
    message = make_message("fixed ")
    cog = make_cog(message)
    cog._send_via_fix_mode = AsyncMock(side_effect=[http_error(code=40005), (None, "reply")])
    cog._add_delete_reaction = AsyncMock()
    media = make_media(3)
    assert await cog._send_message(message, guild_settings=None, medias=[media]) is None
    assert cog._send_via_fix_mode.await_count == 2
    assert cog._send_via_fix_mode.await_args is not None
    assert cog._send_via_fix_mode.await_args.args[2] == []
    assert media.url in message.content


@pytest.mark.usefixtures("db")
async def test_unexpected_send_http_error_is_reraised() -> None:
    message = make_message()
    cog = make_cog(message)
    cog._send_via_fix_mode = AsyncMock(side_effect=http_error(code=50013))
    with pytest.raises(discord.HTTPException):
        await cog._send_message(message, guild_settings=None)


@pytest.mark.usefixtures("db")
async def test_send_fixes_appends_metadata_attachments_and_multiple_sources() -> None:
    message = make_message("fixed")
    attachment = MagicMock(spec=discord.Attachment)
    attachment.url = "https://cdn.test/attachment"
    attachment.to_file = AsyncMock(return_value=make_media(1).file)
    message.attachments = [attachment]
    result = fix_result()
    result.content = "post body"
    result.author_md = "Alice"
    result.sauces = ["https://source.test/1", "https://source.test/2"]
    cog = make_cog(message)
    cog._send_files = AsyncMock(return_value="webhook")
    assert (
        await cog._send_fixes(
            message,
            result,
            guild_settings=GuildSettings(id=1, show_post_content_channels=[2]),
            filesize_limit=10,
        )
        == "webhook"
    )
    assert "post body" in message.content
    assert "-# Alice" in message.content
    assert "||<https://source.test/1>\n<https://source.test/2>||" in message.content
    assert result.medias[0].url == attachment.url
    assert result.sauces == []


@pytest.mark.usefixtures("db")
async def test_send_files_keeps_caption_only_on_first_batch_and_adds_source_button() -> None:
    message = make_message("caption")
    cog = make_cog(message)
    contents = []

    def record_send(message: discord.Message, **kwargs: object) -> str:
        contents.append(message.content)
        view = kwargs["view"]
        assert isinstance(view, discord.ui.View)
        button = view.children[0]
        assert isinstance(button, discord.ui.Button)
        assert button.url == "https://source.test/post"
        return "reply"

    cog._send_message = AsyncMock(side_effect=record_send)
    medias = [Media(url=f"https://cdn.test/{index}") for index in range(11)]
    assert (
        await cog._send_files(
            message, medias, ["https://source.test/post"], guild_settings=None, filesize_limit=1024
        )
        == "reply"
    )
    assert contents[0].startswith("caption\n")
    assert not contents[1].startswith("caption")
    assert "https://cdn.test/10" in contents[1]
    assert not message.content


@pytest.mark.parametrize("action", ["add", "remove"])
@pytest.mark.parametrize("status", [403, 404])
async def test_safe_reactions_tolerate_missing_message_and_permissions(
    action: str, status: int
) -> None:
    message = make_message()
    error = http_error(
        status=status, error_type=discord.Forbidden if status == 403 else discord.NotFound
    )
    if action == "add":
        message.add_reaction.side_effect = error
        await add_reaction_safe(message, "x")
        message.add_reaction.assert_awaited_once_with("x")
    else:
        message.remove_reaction.side_effect = error
        await remove_reaction_safe(message, "x", message.author)
        message.remove_reaction.assert_awaited_once_with("x", message.author)


async def test_delete_and_rotate_reactions_schedule_expiration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = make_message()
    cog = make_cog(message)
    tasks: list[asyncio.Task[None]] = []
    original = asyncio.create_task

    def create(coro: Coroutine[Any, Any, None]) -> asyncio.Task[None]:
        task = original(coro)
        tasks.append(task)
        return task

    monkeypatch.setattr(module.asyncio, "create_task", create)
    sleep = AsyncMock()
    monkeypatch.setattr(module.asyncio, "sleep", sleep)
    await cog._add_delete_reaction(
        message,
        None,
        message,
        disable_delete_reaction=False,
        delete_msg_emoji="❌",
        remove_delete_reaction_after=5,
        remove_rotate_reaction_after=7,
        rotate_fix_reaction=True,
    )
    await asyncio.gather(*tasks)
    assert [call.args[0] for call in message.add_reaction.await_args_list] == ["🔄", "❌"]
    assert {call.args[0] for call in message.remove_reaction.await_args_list} == {"🔄", "❌"}
    assert {call.args[0] for call in sleep.await_args_list} == {5, 7}


@pytest.mark.usefixtures("db")
@pytest.mark.parametrize("code", [50035, 50013])
async def test_delete_reaction_http_error_notifies_user(
    monkeypatch: pytest.MonkeyPatch, code: int
) -> None:
    message = make_message()
    cog = make_cog(message)
    capture = MagicMock()
    monkeypatch.setattr(module, "capture_exception", capture)
    message.add_reaction.side_effect = http_error(code=code)
    await cog._add_delete_reaction(
        message, None, message, disable_delete_reaction=False, delete_msg_emoji="❌"
    )
    message.reply.assert_awaited_once()
    assert capture.call_count == (0 if code == 50035 else 1)


@pytest.mark.usefixtures("db")
async def test_delete_reaction_permission_error_notifies_user() -> None:
    message = make_message()
    message.add_reaction.side_effect = http_error(status=403, error_type=discord.Forbidden)
    await make_cog(message)._add_delete_reaction(
        message, None, message, disable_delete_reaction=False, delete_msg_emoji="❌"
    )
    message.reply.assert_awaited_once()


@pytest.mark.parametrize("disabled", [False, True])
async def test_interactions_never_receive_delete_reactions(disabled: bool) -> None:
    message = make_message()
    await make_cog(message)._add_delete_reaction(
        message,
        make_interaction(message),
        message,
        disable_delete_reaction=disabled,
        delete_msg_emoji="❌",
        rotate_fix_reaction=True,
    )
    message.add_reaction.assert_not_awaited()
