from __future__ import annotations

import asyncio
import io
from typing import TYPE_CHECKING, Any
from unittest.mock import Mock

import pytest

from embed_fixer.utils import misc

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from pathlib import Path


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("plain text &amp; data", "plain text &amp; data"),
        ("<p>Hello <strong>world</strong>!</p>", "Hello world!"),
        ("one<br />two<!-- hidden -->", "onetwo"),
        ("a < b", "a < b"),
    ],
)
def test_remove_html_tags(text: str, expected: str) -> None:
    assert misc.remove_html_tags(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("No URL", []),
        (
            "http://example.com/a https://example.org/b",
            [("http://example.com/a", False), ("https://example.org/b", False)],
        ),
        (
            "||https://example.com/spoiler|| https://example.com/open",
            [("https://example.com/spoiler", True), ("https://example.com/open", False)],
        ),
        ("<https://example.com/hidden> $https://example.com/hidden", []),
        (
            "https://example.com/a\nhttps://example.com/a",
            [("https://example.com/a", False), ("https://example.com/a", False)],
        ),
    ],
)
def test_extract_urls_preserves_spoilers_and_discord_opt_outs(
    text: str, expected: list[tuple[str, bool]]
) -> None:
    assert misc.extract_urls(text) == expected


def test_get_filesize_restores_stream_position() -> None:
    stream = io.BytesIO(b"abcdef")
    stream.seek(2)
    assert misc.get_filesize(stream) == 6
    assert stream.tell() == 2
    assert stream.read() == b"cdef"


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://example.com/path?a=1&b=2#part", "https://example.com/path#part"),
        (
            "https://www.youtube.com/watch?v=abc-123&si=track&t=9",
            "https://www.youtube.com/watch?v=abc-123",
        ),
        (
            "https://m.youtube.com/watch?si=track&v=one&v=two",
            "https://m.youtube.com/watch?v=one&v=two",
        ),
        ("https://notyoutube.com/watch?v=abc", "https://notyoutube.com/watch"),
        ("https://youtu.be/abc?si=track", "https://youtu.be/abc"),
        ("https://youtube.com/watch?x=one#part", "https://youtube.com/watch#part"),
        ("https://example.com/a;b?x=1", "https://example.com/a;b"),
    ],
)
def test_remove_query_params_keeps_content_ids(url: str, expected: str) -> None:
    assert misc.remove_query_params(url) == expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://twitter.com/user/status/1", True),
        ("https://www.twitter.com/user/status/1", True),
        ("https://deep.sub.twitter.com/a", True),
        ("https://nottwitter.com/a", False),
        ("https://twitter.com.evil.example/a", False),
        ("https://example.com/twitter.com", False),
        ("twitter.com/user", False),
    ],
)
def test_domain_in_url_requires_a_hostname_boundary(url: str, expected: bool) -> None:
    assert misc.domain_in_url(url, "twitter.com") is expected


def test_replace_domain_retains_path_parameters_query_and_fragment() -> None:
    assert (
        misc.replace_domain(
            "https://www.twitter.com/user/status/1;param?q=2#photo", "twitter.com", "fxtwitter.com"
        )
        == "https://fxtwitter.com/user/status/1;param?q=2#photo"
    )
    unrelated = "https://nottwitter.com/twitter.com?q=twitter.com"
    assert misc.replace_domain(unrelated, "twitter.com", "fxtwitter.com") == unrelated


@pytest.mark.parametrize(
    ("url", "path", "expected"),
    [
        ("https://example.com/one/", "/two", "https://example.com/one/two"),
        ("https://example.com", "two", "https://example.com/two"),
        ("https://example.com/a?q=1#part", "b/c", "https://example.com/a/b/c?q=1#part"),
    ],
)
def test_append_path_to_url(url: str, path: str, expected: str) -> None:
    assert misc.append_path_to_url(url, path) == expected


@pytest.mark.parametrize("use_factory", [False, True])
async def test_task_factory_keeps_tasks_alive_until_completion(*, use_factory: bool) -> None:
    loop = asyncio.get_running_loop()
    previous_factory = loop.get_task_factory()
    seen_kwargs: list[dict[str, Any]] = []

    def original_factory(
        loop: asyncio.AbstractEventLoop, coro: Coroutine[Any, Any, Any], **kwargs: Any
    ) -> asyncio.Task[Any]:
        seen_kwargs.append(kwargs)
        return asyncio.Task(coro, loop=loop, **kwargs)

    loop.set_task_factory(original_factory if use_factory else None)
    event = asyncio.Event()
    try:
        misc.wrap_task_factory()
        task = asyncio.create_task(event.wait())
        assert task in misc._tasks_set
        event.set()
        await task
        await asyncio.sleep(0)
        assert task not in misc._tasks_set
        assert bool(seen_kwargs) is use_factory
    finally:
        loop.set_task_factory(previous_factory)


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ('[project]\nversion = "2.4.1"\n', "v2.4.1"),
        ("[project]\nname = 'bot'\n", "unknown"),
        ("[project", "unknown"),
        (None, "unknown"),
    ],
)
def test_project_version_handles_missing_and_invalid_metadata(
    content: str | None, expected: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    if content is not None:
        (tmp_path / "pyproject.toml").write_text(content)
    assert misc.get_project_version() == expected


@pytest.mark.parametrize("sentry_enabled", [False, True])
def test_capture_exception_routes_to_configured_sink(
    *, sentry_enabled: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        misc.settings, "sentry_dsn", "https://example.com/1" if sentry_enabled else None
    )
    logger = Mock()
    capture = Mock()
    monkeypatch.setattr(misc, "logger", logger)
    monkeypatch.setattr(misc.sentry_sdk, "capture_exception", capture)
    error = ValueError("bad input")
    misc.capture_exception(error)
    if sentry_enabled:
        capture.assert_called_once_with(error)
        logger.warning.assert_called_once()
        logger.exception.assert_not_called()
    else:
        capture.assert_not_called()
        logger.exception.assert_called_once_with("Exception occurred: bad input")


@pytest.mark.parametrize(
    ("original", "sanitized", "restored"),
    [
        ("Alice", "Alice", "Alice"),
        ("DISCORD Discord discord", "discorɗ discorɗ discorɗ", "discord discord discord"),
        ("myDiscordBot", "mydiscorɗBot", "mydiscordBot"),
    ],
)
def test_username_sanitization(original: str, sanitized: str, restored: str) -> None:
    assert misc.sanitize_username(original) == sanitized
    assert misc.unsanitize_username(sanitized) == restored
