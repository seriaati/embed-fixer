from __future__ import annotations

import asyncio
import io
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import discord
import pytest

from embed_fixer.cogs import fixer as module
from embed_fixer.cogs.fixer import (
    FixerCog,
    Media,
    MockMessage,
    PostExtractionResult,
    _apply_fix_to_url,
    _get_next_fix_method,
    _parse_new_domain_parts,
    _reverse_parse_fixed_url,
)
from embed_fixer.fixes import (
    DOMAINS,
    AppendURLFix,
    Domain,
    DomainId,
    FixMethod,
    ReplaceFix,
    Website,
)
from embed_fixer.models import GuildFixMethod, GuildSettings
from tests.support.fixer import make_cog, make_message

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any


@pytest.mark.parametrize(
    ("value", "expected"),
    [("example.com", ("example.com", "")), ("example.com/path/sub", ("example.com", "/path/sub"))],
)
def test_split_fix_host_and_path(value: str, expected: tuple[str, str]) -> None:
    assert _parse_new_domain_parts(value) == expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://fxtwitter.com/alice/status/123", "https://twitter.com/alice/status/123"),
        ("https://vxtwitter.com/alice/status/123", "https://twitter.com/alice/status/123"),
        ("https://phixiv.net/en/artworks/123", "https://pixiv.net/en/artworks/123"),
    ],
)
def test_reverse_fixed_urls(url: str, expected: str) -> None:
    result = _reverse_parse_fixed_url(url)
    assert result is not None
    assert result[2] == expected


@pytest.mark.parametrize("url", ["https://example.com/a", "https://fxtwitter.com.evil.test/a"])
def test_unknown_fixed_urls_are_not_recognized(url: str) -> None:
    assert _reverse_parse_fixed_url(url) is None


def test_reverse_specific_path_and_append_fixes(monkeypatch: pytest.MonkeyPatch) -> None:
    method = FixMethod(
        id=1000,
        name="test",
        fixes=[
            ReplaceFix(old_domain="original.test", new_domain="proxy.test"),
            ReplaceFix(old_domain="special.test", new_domain="proxy.test/prefix"),
            AppendURLFix(domain="append.test/fix"),
        ],
    )
    domain = Domain(id=DomainId.TWITTER, name="test", websites=[], fix_methods=[method])
    monkeypatch.setattr(module, "DOMAINS", [domain])
    result = _reverse_parse_fixed_url("https://proxy.test/prefix/post?x=1#part")
    assert result is not None
    assert result[2] == "https://special.test/post?x=1#part"
    appended = _reverse_parse_fixed_url(
        "https://append.test/fix?url=https%3A%2F%2Foriginal.test%2Fa"
    )
    assert appended is not None
    assert appended[2] == "https://original.test/a"
    assert _reverse_parse_fixed_url("https://append.test/fix") is None
    assert _reverse_parse_fixed_url("https://append.test/other?url=x") is None
    prefix_result = _reverse_parse_fixed_url("https://proxy.test/prefix")
    assert prefix_result is not None
    assert prefix_result[2] == "https://special.test/"


def test_fix_rotation_wraps_and_rejects_unknown_method() -> None:
    domain = next(domain for domain in DOMAINS if domain.id == DomainId.TWITTER)
    assert _get_next_fix_method(domain, domain.fix_methods[-1].id) is domain.fix_methods[0]
    assert _get_next_fix_method(domain, domain.fix_methods[0].id) is domain.fix_methods[1]
    assert _get_next_fix_method(domain, -1) is None
    one = Domain(id=DomainId.TWITTER, name="one", websites=[], fix_methods=domain.fix_methods[:1])
    assert _get_next_fix_method(one, one.fix_methods[0].id) is None


@pytest.mark.parametrize(
    ("fix", "url", "domain_id", "expected"),
    [
        (
            ReplaceFix(old_domain="a.test", new_domain="b.test"),
            "https://a.test/p?q=1",
            DomainId.TWITTER,
            "https://b.test/p?q=1",
        ),
        (
            ReplaceFix(old_domain="a.test", new_domain="b.test"),
            "https://other.test/p",
            DomainId.TWITTER,
            None,
        ),
        (
            AppendURLFix(domain="proxy.test"),
            "https://facebook.com/v/123",
            DomainId.FACEBOOK,
            "https://proxy.test?url=https%3A%2F%2Ffacebook.com%2Fr%2F123",
        ),
    ],
)
def test_apply_fix_variants(
    fix: ReplaceFix | AppendURLFix, url: str, domain_id: DomainId, expected: str | None
) -> None:
    method = FixMethod(id=1000, name="test", fixes=[fix])
    assert _apply_fix_to_url(url, method, domain_id) == expected


@pytest.mark.parametrize(
    ("settings", "channel_id", "expected"),
    [
        (None, 2, False),
        (GuildSettings(id=1), 2, False),
        (GuildSettings(id=1, disable_fix_channels=[2]), 2, True),
        (GuildSettings(id=1, enable_fix_channels=[3]), 2, True),
        (GuildSettings(id=1, enable_fix_channels=[2]), 2, False),
    ],
)
def test_channel_allow_and_deny_lists(
    settings: GuildSettings | None, channel_id: int, expected: bool
) -> None:
    assert FixerCog._skip_channel(settings, channel_id) is expected


@pytest.mark.parametrize("domain_id", [DomainId.TWITTER, DomainId.PIXIV, DomainId.KEMONO])
@pytest.mark.parametrize("is_nsfw", [False, True])
async def test_sensitive_content_gate(domain_id: DomainId, is_nsfw: bool) -> None:
    cog = make_cog()
    cog.fetch_info.pixiv_is_nsfw = AsyncMock(return_value=True)
    cog.fetch_info.twitter_is_nsfw = AsyncMock(return_value=True)
    domain = next(domain for domain in DOMAINS if domain.id == domain_id)
    assert await cog._nsfw_skip("https://example.com", domain, is_nsfw_channel=is_nsfw) is (
        not is_nsfw
    )
    if is_nsfw:
        cog.fetch_info.pixiv_is_nsfw.assert_not_awaited()
        cog.fetch_info.twitter_is_nsfw.assert_not_awaited()


@pytest.mark.usefixtures("db")
async def test_guild_selected_fix_and_stale_selection_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = await GuildSettings.create(1)
    domain = next(domain for domain in DOMAINS if domain.id == DomainId.TWITTER)
    selected = domain.fix_methods[1]
    record = await GuildFixMethod.create(guild_id=1, domain_id=domain.id, fix_id=selected.id)
    assert await FixerCog._determine_fix_method(settings, domain) is selected
    tasks: list[asyncio.Task[None]] = []
    original_create_task = asyncio.create_task

    def create_task(coro: Coroutine[Any, Any, None]) -> asyncio.Task[None]:
        task = original_create_task(coro)
        tasks.append(task)
        return task

    monkeypatch.setattr(module.asyncio, "create_task", create_task)
    record.fix_id = -1
    await record.save()
    assert await FixerCog._determine_fix_method(settings, domain) is domain.default_fix_method
    assert len(tasks) == 1
    await asyncio.gather(*tasks)
    assert not await GuildFixMethod.filter(id=record.pk).exists()


async def test_domain_without_methods_and_default_selection() -> None:
    domain = Domain(id=DomainId.TWITTER, name="none", websites=[], fix_methods=[])
    assert await FixerCog._determine_fix_method(None, domain) is None
    twitter = next(domain for domain in DOMAINS if domain.id == DomainId.TWITTER)
    assert await FixerCog._determine_fix_method(None, twitter) is twitter.default_fix_method


@pytest.mark.usefixtures("db")
async def test_find_fixes_rewrites_text_preserves_spoilers_and_cleans_tracking() -> None:
    message = make_message("hello ||https://www.x.com/alice/status/123?utm_source=test||")
    cog = make_cog(message)
    cog.fetch_info.twitter_is_nsfw = AsyncMock(return_value=False)
    settings = GuildSettings(id=1, translate_target_lang="ja")
    result = await cog._find_fixes(message, settings=settings, filesize_limit=1024)
    assert result.fix_found
    assert message.content == "hello ||https://fixupx.com/alice/status/123/ja||"
    assert result.urls == ["https://www.x.com/alice/status/123"]
    assert not result.medias


@pytest.mark.parametrize("content", ["plain text", "https://unknown.test/a", "https://[broken/"])
@pytest.mark.usefixtures("db")
async def test_find_fixes_ignores_unknown_and_invalid_urls(content: str) -> None:
    message = make_message(content)
    result = await make_cog(message)._find_fixes(message, settings=None, filesize_limit=1024)
    assert not result.fix_found
    assert message.content == content


@pytest.mark.usefixtures("db")
async def test_find_fixes_reports_sensitive_url_skip() -> None:
    message = make_message("https://x.com/alice/status/123")
    cog = make_cog(message)
    cog.fetch_info.twitter_is_nsfw = AsyncMock(return_value=True)
    result = await cog._find_fixes(message, settings=None, filesize_limit=1024)
    assert not result.fix_found
    assert result.nsfw_skipped
    assert message.content == "https://x.com/alice/status/123"


@pytest.mark.usefixtures("db")
async def test_media_extraction_strips_source_and_falls_back_for_oversized_files() -> None:
    message = make_message("hello ||https://x.com/alice/status/123||")
    cog = make_cog(message)
    cog.fetch_info.twitter_is_nsfw = AsyncMock(return_value=False)
    file = discord.File(io.BytesIO(b"oversize"), filename="photo.png")
    cog._extract_post_info = AsyncMock(
        return_value=PostExtractionResult(
            medias=[Media(url="https://cdn.test/photo", file=file)],
            content="post text",
            author_md="Alice 😀",
        )
    )
    result = await cog._find_fixes(
        message, settings=None, filesize_limit=2, extract_media=True, is_ctx_menu=True
    )
    assert result.fix_found
    assert result.medias[0].file is None
    assert result.sauces == ["https://x.com/alice/status/123"]
    assert result.content == "post text"
    assert result.author_md == "Alice "
    assert message.content == "hello "
    assert cog._extract_post_info.await_args is not None
    assert cog._extract_post_info.await_args.kwargs["spoiler"] is True


@pytest.mark.usefixtures("db")
@pytest.mark.parametrize("extract_only", [True, False])
async def test_failed_extraction_can_fall_back_to_embed_fix(extract_only: bool) -> None:
    message = make_message("https://x.com/alice/status/123")
    cog = make_cog(message)
    cog.fetch_info.twitter_is_nsfw = AsyncMock(return_value=False)
    cog._extract_post_info = AsyncMock(
        return_value=PostExtractionResult(medias=[], content="", author_md="")
    )
    result = await cog._find_fixes(
        message,
        settings=GuildSettings(id=1, extract_media_channels=[2]),
        filesize_limit=1024,
        extract_media=extract_only,
        is_ctx_menu=True,
    )
    assert result.fix_found is (not extract_only)


@pytest.mark.parametrize("disabled", [False, True])
def test_disabled_by_default_domains_require_explicit_enable(disabled: bool) -> None:
    settings = GuildSettings(id=1, enabled_domains=[] if disabled else [DomainId.YOUTUBE])
    domain, _ = FixerCog._get_matching_domain_website(
        settings, "https://www.youtube.com/watch?v=123"
    )
    assert (domain is None) is disabled
    assert FixerCog._get_matching_domain_website(
        GuildSettings(id=1, disabled_domains=[DomainId.TWITTER]), "https://x.com/alice/status/123"
    ) == (None, None)


@pytest.mark.usefixtures("db")
async def test_skip_method_and_append_fix_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    method = FixMethod(id=1000, name="proxy", fixes=[AppendURLFix(domain="proxy.test")])
    website = Website(r"https://facebook.com/", skip_method_ids=[1000])
    domain = Domain(id=DomainId.FACEBOOK, name="test", websites=[website], fix_methods=[method])
    monkeypatch.setattr(module, "DOMAINS", [domain])
    message = make_message("https://facebook.com/v/123")
    cog = make_cog(message)
    assert not (await cog._find_fixes(message, settings=None, filesize_limit=1024)).fix_found
    website.skip_method_ids = None
    assert (await cog._find_fixes(message, settings=None, filesize_limit=1024)).fix_found
    assert message.content == "https://proxy.test?url=https%3A%2F%2Ffacebook.com%2Fr%2F123"


def test_slash_message_starts_with_independent_attachment_lists() -> None:
    message = make_message()
    first = MockMessage("a", message.channel, None, message.author)
    second = MockMessage("b", message.channel, None, message.author)
    first.attachments.append(message)
    assert not second.attachments
    assert first.id == 0
    assert not first.tts
    assert first.reference is None
