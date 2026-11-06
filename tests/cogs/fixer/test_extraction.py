from __future__ import annotations

import asyncio
import io
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from embed_fixer.cogs import fixer as module
from embed_fixer.cogs.fixer import Media, PostExtractionResult
from embed_fixer.fixes import Domain, DomainId, FixMethod, ReplaceFix, Website
from embed_fixer.models import GuildSettings
from tests.support.fixer import fix_result, http_error, make_cog, make_interaction, make_message

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any

pytestmark = pytest.mark.usefixtures("db")


@pytest.mark.parametrize(
    "domain_id",
    [DomainId.TWITTER, DomainId.BLUESKY, DomainId.INSTAGRAM, DomainId.PIXIV, DomainId.KEMONO],
)
async def test_extraction_builds_downloads_and_falls_back_to_media_urls(
    monkeypatch: pytest.MonkeyPatch, domain_id: DomainId
) -> None:
    cog = make_cog()
    url = "https://original.test/post?tracking=1"
    info = SimpleNamespace(
        text="a" * 2100,
        caption="a" * 2100,
        description="a" * 2100,
        author_md="Author 😀",
        medias=[SimpleNamespace(url="https://cdn.test/1")],
        media=[SimpleNamespace(url="https://cdn.test/1")],
        media_urls=["https://cdn.test/1"],
        image_urls=["https://cdn.test/1"],
        fallback_image_urls=["https://cdn.test/small"],
        record=SimpleNamespace(text="a" * 2100),
        is_ugoira=False,
    )
    method = {
        DomainId.TWITTER: "twitter",
        DomainId.BLUESKY: "bluesky",
        DomainId.INSTAGRAM: "instagram",
        DomainId.PIXIV: "pixiv",
        DomainId.KEMONO: "kemono",
    }[domain_id]
    fetch = AsyncMock(return_value=["https://cdn.test/1"] if domain_id is DomainId.KEMONO else info)
    monkeypatch.setattr(cog.fetch_info, method, fetch)
    downloader = MagicMock()
    downloader.files = {}
    downloader.ugoira_file = None
    downloader.start = AsyncMock()
    factory = MagicMock(return_value=downloader)
    monkeypatch.setattr(module, "MediaDownloader", factory)
    result = await cog._extract_post_info(domain_id, url, filesize_limit=100, spoiler=True)
    assert result.medias == [Media(url="https://cdn.test/1")]
    assert len(result.content) == (0 if domain_id is DomainId.KEMONO else 2000)
    assert result.author_md == ("" if domain_id is DomainId.KEMONO else "Author ")
    downloader.start.assert_awaited_once_with(spoiler=True, filesize_limit=100)
    assert factory.call_args.kwargs["media_urls"] == ["https://cdn.test/1"]
    if domain_id is DomainId.PIXIV:
        assert factory.call_args.kwargs["fallback_urls"] == {
            "https://cdn.test/1": "https://cdn.test/small"
        }
    if domain_id is DomainId.INSTAGRAM:
        fetch.assert_awaited_once_with("https://original.test/post?tracking=1")


@pytest.mark.parametrize(
    "domain_id",
    [DomainId.TWITTER, DomainId.BLUESKY, DomainId.INSTAGRAM, DomainId.PIXIV, DomainId.YOUTUBE],
)
async def test_extraction_missing_metadata_or_unsupported_platform_returns_empty(
    monkeypatch: pytest.MonkeyPatch, domain_id: DomainId
) -> None:
    cog = make_cog()
    for name in ("twitter", "bluesky", "instagram", "pixiv"):
        monkeypatch.setattr(cog.fetch_info, name, AsyncMock(return_value=None))
    factory = MagicMock(return_value=SimpleNamespace(files={}, ugoira_file=None, start=AsyncMock()))
    monkeypatch.setattr(module, "MediaDownloader", factory)
    result = await cog._extract_post_info(
        domain_id, "https://original.test/post", filesize_limit=100
    )
    assert not result.medias
    assert not result.content
    assert not result.author_md


async def test_extraction_returns_converted_animation_and_downloaded_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cog = make_cog()
    animation = discord.File(io.BytesIO(b"mp4"), filename="animation.mp4")
    image = discord.File(io.BytesIO(b"png"), filename="image.png")
    meta = MagicMock()
    monkeypatch.setattr(
        cog.fetch_info,
        "pixiv",
        AsyncMock(
            return_value=SimpleNamespace(
                description="body",
                author_md="Artist",
                image_urls=["https://cdn.test/1"],
                fallback_image_urls=[""],
                is_ugoira=True,
                ugoira_meta=meta,
            )
        ),
    )
    downloader = SimpleNamespace(
        files={"https://cdn.test/1": image}, ugoira_file=animation, start=AsyncMock()
    )
    factory = MagicMock(return_value=downloader)
    monkeypatch.setattr(module, "MediaDownloader", factory)
    result = await cog._extract_post_info(
        DomainId.PIXIV, "https://pixiv.net/artworks/123", filesize_limit=100
    )
    assert [media.file for media in result.medias] == [animation, image]
    assert factory.call_args.kwargs["ugoira_meta"] is meta
    assert not factory.call_args.kwargs["fallback_urls"]


async def test_extraction_failure_is_contained_and_does_not_download(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cog = make_cog()
    monkeypatch.setattr(
        cog.fetch_info, "twitter", AsyncMock(side_effect=ValueError("malformed API response"))
    )
    factory = MagicMock()
    monkeypatch.setattr(module, "MediaDownloader", factory)
    result = await cog._extract_post_info(
        DomainId.TWITTER, "https://x.com/a/status/1", filesize_limit=100
    )
    assert not result.medias
    factory.assert_not_called()


async def test_extraction_channel_removes_plain_source_and_shows_progress(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = make_message("caption https://x.com/alice/status/123")
    cog = make_cog(message)
    monkeypatch.setattr(cog.fetch_info, "twitter_is_nsfw", AsyncMock(return_value=False))
    monkeypatch.setattr(
        cog,
        "_extract_post_info",
        AsyncMock(
            return_value=PostExtractionResult(
                medias=[Media(url="https://cdn.test/a")], content="", author_md=""
            )
        ),
    )
    created: list[asyncio.Task[Any]] = []
    original = asyncio.create_task

    def schedule(coro: Coroutine[Any, Any, Any]) -> asyncio.Task[Any]:
        task = original(coro)
        created.append(task)
        return task

    monkeypatch.setattr(module.asyncio, "create_task", schedule)
    result = await cog._find_fixes(
        message, settings=GuildSettings(id=1, extract_media_channels=[2]), filesize_limit=100
    )
    await asyncio.gather(*created)
    assert result.fix_found
    assert message.content == "caption "
    message.add_reaction.assert_awaited_once_with("⌛")


async def test_ad_supported_service_recommends_original_link_button(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    method = FixMethod(
        id=1000,
        name="ads",
        has_ads=True,
        fixes=[ReplaceFix(old_domain="original.test", new_domain="ads.test")],
    )
    domain = Domain(
        id=DomainId.TWITTER,
        name="test",
        websites=[Website(r"https://original.test/")],
        fix_methods=[method],
    )
    monkeypatch.setattr(module, "DOMAINS", [domain])
    message = make_message("https://original.test/post")
    cog = make_cog(message)
    monkeypatch.setattr(cog.fetch_info, "twitter_is_nsfw", AsyncMock(return_value=False))
    result = await cog._find_fixes(
        message, settings=GuildSettings(id=1, show_original_link_btn=False), filesize_limit=100
    )
    assert result.fix_found
    assert message.content.startswith("-# ")
    assert message.content.endswith("https://ads.test/post")


async def test_reply_to_fixed_message_uses_recorded_author_and_suppresses_pings() -> None:
    message = make_message()
    reference = make_message()
    cog = make_cog(message)
    author = MagicMock(spec=discord.Member)
    author.id = 11
    author.bot = False
    author.mention = "<@11>"
    cog._get_fixed_message_author = AsyncMock(return_value=author)
    await cog._handle_reply(message, reference)
    assert "<@11>" in message.reply.await_args.args[0]
    assert message.reply.await_args.kwargs["mention_author"] is False
    assert message.reply.await_args.kwargs["silent"] is True


@pytest.mark.parametrize("reason", ["dollar", "dm", "missing", "bot", "same_author"])
async def test_reply_to_fixed_message_ignores_ineligible_authors(reason: str) -> None:
    message = make_message()
    reference = make_message()
    cog = make_cog(message)
    author = MagicMock(spec=discord.Member)
    author.id = 11
    author.bot = False
    if reason == "dollar":
        message.content = "$do not ping"
    elif reason == "dm":
        message.guild = None
    elif reason == "bot":
        author.bot = True
    elif reason == "same_author":
        author.id = 10
    cog._get_fixed_message_author = AsyncMock(return_value=None if reason == "missing" else author)
    await cog._handle_reply(message, reference)
    message.reply.assert_not_awaited()


@pytest.mark.parametrize("status", [403, 400])
@pytest.mark.parametrize("code", [50035, 50013])
async def test_webhook_reply_errors_are_reported_selectively(
    monkeypatch: pytest.MonkeyPatch, status: int, code: int
) -> None:
    message = make_message()
    cog = make_cog(message)
    author = MagicMock(spec=discord.Member)
    author.id = 11
    author.bot = False
    cog._get_fixed_message_author = AsyncMock(return_value=author)
    message.reply.side_effect = http_error(
        status=status,
        code=code,
        error_type=discord.Forbidden if status == 403 else discord.HTTPException,
    )
    capture = MagicMock()
    monkeypatch.setattr(module, "capture_exception", capture)
    await cog._handle_reply(message, make_message())
    assert capture.call_count == int(status != 403 and code != 50035)


async def test_non_fixed_reply_message_routes_to_original_author() -> None:
    message = make_message()
    reference = make_message()
    reference.webhook_id = 77
    message.reference = SimpleNamespace(resolved=reference)
    cog = make_cog(message)
    cog._find_fixes = AsyncMock(return_value=fix_result(found=False))
    cog._handle_reply = AsyncMock()
    await cog.embed_fixer(message)
    cog._handle_reply.assert_awaited_once_with(message, reference)


async def test_context_menu_success_and_forbidden_send() -> None:
    message = make_message()
    cog = make_cog(message)
    cog._find_fixes = AsyncMock(return_value=fix_result())
    cog._send_fixes = AsyncMock(side_effect=http_error(status=403, error_type=discord.Forbidden))
    interaction = make_interaction(message)
    await cog.fix_embed(interaction, message)
    cog._send_fixes.side_effect = None
    await cog.extract_medias(interaction, message)
    assert [call.kwargs["extract_media"] for call in cog._find_fixes.await_args_list] == [
        False,
        True,
    ]


@pytest.mark.parametrize("nsfw", [False, True])
async def test_slash_empty_result_deletes_public_placeholder(nsfw: bool) -> None:
    message = make_message(with_guild=False)
    cog = make_cog(message)
    cog._find_fixes = AsyncMock(return_value=fix_result(found=False, nsfw=nsfw))
    interaction = make_interaction(message)
    callback = cast("Any", cog.fix_url_command.callback)
    await callback(cog, interaction, "https://unknown.test")
    interaction.delete_original_response.assert_awaited_once()
    assert interaction.followup.send.await_args.kwargs["ephemeral"] is True


async def test_slash_extraction_limits_attachments_and_adds_source_button() -> None:
    message = make_message(with_guild=False)
    cog = make_cog(message)
    result = fix_result()
    file = discord.File(io.BytesIO(b"data"), filename="photo.png")
    result.medias = [Media(url="https://cdn.test/a", file=file)] + [
        Media(url=f"https://cdn.test/{index}") for index in range(11)
    ]
    result.sauces = ["https://source.test/post"]
    cog._find_fixes = AsyncMock(return_value=result)
    interaction = make_interaction(message)
    callback = cast("Any", cog.fix_url_command.callback)
    await callback(cog, interaction, "https://source.test/post", True)
    payload = interaction.followup.send.await_args
    assert payload.kwargs["files"] == [file]
    assert payload.kwargs["view"].children[0].url == "https://source.test/post"
    assert "https://cdn.test/8" in payload.args[0]
    assert "https://cdn.test/9" not in payload.args[0]


async def test_cog_registers_and_unregisters_context_menus(monkeypatch: pytest.MonkeyPatch) -> None:
    cog = make_cog()
    start = MagicMock()
    cancel = MagicMock()
    monkeypatch.setattr(cog._purge_fixed_message_records, "start", start)
    monkeypatch.setattr(cog._purge_fixed_message_records, "cancel", cancel)
    await cog.cog_load()
    await cog.cog_unload()
    bot = cast("MagicMock", cog.bot)
    assert bot.tree.add_command.call_count == 2
    assert bot.tree.remove_command.call_count == 2
    start.assert_called_once()
    cancel.assert_called_once()
    bot.add_cog = AsyncMock()
    await module.setup(bot)
    assert bot.add_cog.await_args is not None
    assert isinstance(bot.add_cog.await_args.args[0], module.FixerCog)


async def test_downloaded_file_is_delivered_with_source_link_and_tracked_author() -> None:
    message = make_message("caption")
    sent = make_message()
    sent.id = 200
    message.reply.return_value = sent
    cog = make_cog(message)
    file = discord.File(io.BytesIO(b"image"), filename="image.png")
    result = fix_result()
    result.medias = [Media(url="https://cdn.test/image", file=file)]
    result.sauces = ["https://source.test/post"]
    settings = GuildSettings(
        id=1,
        fix_mode=module.FixMode.REPLY,
        disable_delete_reaction=True,
        show_original_link_btn=False,
    )
    assert (
        await cog._send_fixes(message, result, guild_settings=settings, filesize_limit=1024)
        == "reply"
    )
    message.reply.assert_awaited_once()
    payload = message.reply.await_args
    assert payload.args == ("caption",)
    assert payload.kwargs["files"] == [file]
    assert payload.kwargs["view"].children[0].url == "https://source.test/post"
    record = await module.FixedMessage.get(id=200)
    assert (record.author_id, record.send_type) == (10, "reply")


@pytest.mark.parametrize("disable_spoiler", [False, True])
@pytest.mark.parametrize("thread", [False, True])
async def test_sensitive_channel_extraction_respects_image_spoiler_preference(
    *, disable_spoiler: bool, thread: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    message = make_message("https://x.com/alice/status/123")
    message.channel.nsfw = True
    if thread:
        parent = message.channel
        message.channel = MagicMock(spec=discord.Thread)
        message.channel.parent = parent
        message.channel.id = 2
    cog = make_cog(message)
    fetch = AsyncMock(
        return_value=PostExtractionResult(
            medias=[Media(url="https://cdn.test/image")], content="", author_md=""
        )
    )
    monkeypatch.setattr(cog, "_extract_post_info", fetch)
    sensitive = AsyncMock(return_value=True)
    monkeypatch.setattr(cog.fetch_info, "twitter_is_nsfw", sensitive)
    settings = GuildSettings(id=1, disable_image_spoilers=[2] if disable_spoiler else [])
    result = await cog._find_fixes(
        message, settings=settings, filesize_limit=1024, extract_media=True, is_ctx_menu=True
    )
    assert result.fix_found
    assert fetch.await_args is not None
    assert fetch.await_args.kwargs["spoiler"] is (not disable_spoiler)
    sensitive.assert_not_awaited()
