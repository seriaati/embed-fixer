from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, patch
from urllib.parse import urlsplit

import aiohttp
import pytest
import pytest_asyncio
from aiohttp import web
from pydantic import ValidationError

from embed_fixer.utils.fetch_info import (
    BskyPost,
    InstagramPost,
    PixivArtwork,
    PostInfoFetcher,
    TwitterPost,
    UgoiraMeta,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from aiohttp.pytest_plugin import AiohttpServer


@dataclass
class FetchAPI:
    fetcher: PostInfoFetcher
    responses: dict[str, tuple[int, object]]
    requests: list[tuple[str, dict[str, str], dict[str, str]]]
    urls: list[str]


@pytest_asyncio.fixture
async def fetch_api(aiohttp_server: AiohttpServer) -> AsyncIterator[FetchAPI]:
    responses: dict[str, tuple[int, object]] = {}
    requests: list[tuple[str, dict[str, str], dict[str, str]]] = []
    urls: list[str] = []

    async def respond(request: web.Request) -> web.Response:
        await request.read()
        requests.append((request.path, dict(request.query), dict(request.headers)))
        status, payload = responses[request.path]
        return web.json_response(payload, status=status)

    app = web.Application()
    app.router.add_get("/{path:.*}", respond)
    server = await aiohttp_server(app)
    async with aiohttp.ClientSession() as session:
        original_get = session.get

        def redirect(url: str, **kwargs: Any) -> Any:
            urls.append(url)
            parsed = urlsplit(url)
            path = parsed.path + (f"?{parsed.query}" if parsed.query else "")
            return original_get(server.make_url(path), **kwargs)

        with patch.object(session, "get", side_effect=redirect):
            yield FetchAPI(PostInfoFetcher(session), responses, requests, urls)


def pixiv_payload(**updates: Any) -> dict[str, Any]:
    return {
        "illustId": "123",
        "title": "An artwork",
        "description": "<p>Hello</p>  <a href='https://example.com'>world</a>",
        "tags": {"tags": [{"tag": "art"}, {"tag": "R-18"}, {}]},
        "userName": "Artist",
        "userId": "42",
        "createDate": "2026-01-01T12:00:00+00:00",
        **updates,
    }


def twitter_payload(**updates: Any) -> dict[str, Any]:
    return {
        "author": {
            "id": "42",
            "name": "An author",
            "screen_name": "artist",
            "url": "https://x.com/artist",
        },
        "text": "A post",
        "media": {
            "all": [
                {"type": "photo", "url": "https://media/one.jpg", "width": 10, "height": 20},
                {"type": "video", "url": "https://media/two.mp4", "width": 30, "height": 40},
                {"type": "gif", "url": "https://media/three.gif", "width": 50, "height": 60},
                {"type": "audio", "url": "https://media/four.mp3", "width": 0, "height": 0},
            ]
        },
        **updates,
    }


def bluesky_payload(**updates: Any) -> dict[str, Any]:
    return {
        "cid": "post-cid",
        "author": {"did": "did:plc:artist", "handle": "artist.test", "displayName": "Artist"},
        "record": {"text": "A Bluesky post"},
        **updates,
    }


@pytest.mark.parametrize(
    ("method", "url", "expected"),
    [
        ("_extract_pixiv_id", "https://www.pixiv.net/artworks/123", "123"),
        ("_extract_pixiv_id", "https://www.pixiv.net/en/artworks/456", "456"),
        ("_extract_pixiv_id", "https://www.pixiv.net/users/123", None),
        ("_extract_twitter_details", "https://twitter.com/user/status/123", ("user", "123")),
        ("_extract_twitter_details", "https://x.com/user/status/456/photo/1", ("user", "456")),
        ("_extract_twitter_details", "https://x.com/user", None),
        ("_extract_tweet_photo_index", "https://x.com/u/status/1/photo/2", 1),
        ("_extract_tweet_photo_index", "https://x.com/u/status/1", None),
        ("_extract_iwara_id", "https://www.iwara.tv/video/Ab123/title", "Ab123"),
        ("_extract_iwara_id", "https://www.iwara.tv/profile/Ab123", None),
        ("_extract_b23_slug", "https://b23.tv/Ab_123", "Ab_123"),
        ("_extract_b23_slug", "https://bilibili.com/video/BV123", None),
        ("_extract_bilibili_id", "https://www.bilibili.com/video/BV123", "BV123"),
        ("_extract_bilibili_id", "https://b23.tv/Ab123", None),
    ],
)
def test_extract_platform_identifiers(method: str, url: str, expected: object) -> None:
    assert getattr(PostInfoFetcher, method)(url) == expected


async def test_pixiv_pages_request_and_model_normalization(fetch_api: FetchAPI) -> None:
    fetch_api.responses["/ajax/illust/123"] = (200, {"body": pixiv_payload()})
    fetch_api.responses["/ajax/illust/123/pages"] = (
        200,
        {"body": [{"urls": {"original": "https://original", "regular": "https://regular"}}, {}]},
    )
    artwork = await fetch_api.fetcher.pixiv("https://www.pixiv.net/en/artworks/123")
    assert artwork is not None
    assert artwork.id == 123
    assert artwork.image_urls == ["https://original", ""]
    assert artwork.fallback_image_urls == ["https://regular", ""]
    assert artwork.description == "Hello\nworld"
    assert artwork.tags == ["art", "R-18", ""]
    assert artwork.author_md == "[Artist](<https://www.pixiv.net/users/42>)"
    assert artwork.created_at.utcoffset() is not None
    assert not artwork.is_ugoira
    assert fetch_api.requests[0][1] == {"lang": "jp"}
    assert fetch_api.requests[0][2]["Referer"] == "https://www.pixiv.net/"
    assert fetch_api.urls == [
        "https://www.pixiv.net/ajax/illust/123?lang=jp",
        "https://www.pixiv.net/ajax/illust/123/pages",
    ]


@pytest.mark.parametrize("payload", [{}, {"body": None}])
async def test_pixiv_missing_body_returns_none(fetch_api: FetchAPI, payload: object) -> None:
    fetch_api.responses["/ajax/illust/123"] = (200, payload)
    assert await fetch_api.fetcher.pixiv("https://www.pixiv.net/artworks/123") is None


@pytest.mark.parametrize("stage", ["artwork", "pages", "ugoira"])
async def test_pixiv_failed_request_returns_none(fetch_api: FetchAPI, stage: str) -> None:
    fetch_api.responses["/ajax/illust/123"] = (
        503 if stage == "artwork" else 200,
        {"body": pixiv_payload(illustType=2 if stage == "ugoira" else 0)},
    )
    fetch_api.responses["/ajax/illust/123/pages"] = (403, {})
    fetch_api.responses["/ajax/illust/123/ugoira_meta"] = (404, {})
    assert await fetch_api.fetcher.pixiv("https://www.pixiv.net/artworks/123") is None


async def test_pixiv_invalid_url_does_not_fetch(fetch_api: FetchAPI) -> None:
    assert await fetch_api.fetcher.pixiv("https://www.pixiv.net/users/42") is None
    assert fetch_api.requests == []


@pytest.mark.parametrize(
    "metadata",
    [
        None,
        {},
        {
            "src": "https://small.zip",
            "originalSrc": "https://large.zip",
            "mime_type": "image/jpeg",
            "frames": [{"file": "0.jpg", "delay": 100}],
        },
    ],
)
async def test_pixiv_ugoira_metadata(fetch_api: FetchAPI, metadata: object) -> None:
    fetch_api.responses["/ajax/illust/123"] = (200, {"body": pixiv_payload(illustType=2)})
    fetch_api.responses["/ajax/illust/123/ugoira_meta"] = (200, {"body": metadata})
    artwork = await fetch_api.fetcher.pixiv("https://www.pixiv.net/artworks/123")
    assert artwork is not None
    assert artwork.is_ugoira
    assert fetch_api.urls == [
        "https://www.pixiv.net/ajax/illust/123?lang=jp",
        "https://www.pixiv.net/ajax/illust/123/ugoira_meta",
    ]
    if metadata:
        assert artwork.ugoira_meta is not None
        assert artwork.ugoira_meta.original_src == "https://large.zip"
        assert artwork.ugoira_meta.frames[0].delay == 100
    else:
        assert artwork.ugoira_meta is None


async def test_pixiv_missing_pages_defaults_to_empty(fetch_api: FetchAPI) -> None:
    fetch_api.responses["/ajax/illust/123"] = (200, {"body": pixiv_payload()})
    fetch_api.responses["/ajax/illust/123/pages"] = (200, {})
    artwork = await fetch_api.fetcher.pixiv("https://www.pixiv.net/artworks/123")
    assert artwork is not None
    assert artwork.image_urls == artwork.fallback_image_urls == []


@pytest.mark.parametrize("sensitive", [False, True, None])
async def test_pixiv_nsfw_uses_r18_tag(fetch_api: FetchAPI, sensitive: bool | None) -> None:
    artwork = (
        None
        if sensitive is None
        else PixivArtwork(**pixiv_payload(tags={"tags": [{"tag": "R-18" if sensitive else "art"}]}))
    )
    with patch.object(fetch_api.fetcher, "pixiv", AsyncMock(return_value=artwork)):
        assert await fetch_api.fetcher.pixiv_is_nsfw("https://pixiv.net/artworks/123") is bool(
            sensitive
        )


async def test_twitter_filters_media_and_selects_photo(fetch_api: FetchAPI) -> None:
    fetch_api.responses["/artist/status/123"] = (200, {"tweet": twitter_payload()})
    post = await fetch_api.fetcher.twitter("https://x.com/artist/status/123/photo/2")
    assert post is not None
    assert [media.url for media in post.medias] == ["https://media/two.mp4"]
    assert post.author_md == "[An author (@artist)](<https://x.com/artist>)"
    assert post.author.avatar_url is None
    assert post.author.banner_url is None
    assert fetch_api.urls == ["https://api.fxtwitter.com/artist/status/123"]


@pytest.mark.parametrize("suffix", ["", "/photo/99"])
async def test_twitter_keeps_all_supported_media(fetch_api: FetchAPI, suffix: str) -> None:
    fetch_api.responses["/artist/status/123"] = (200, {"tweet": twitter_payload()})
    post = await fetch_api.fetcher.twitter(f"https://twitter.com/artist/status/123{suffix}")
    assert post is not None
    assert [media.type for media in post.medias] == ["photo", "video", "gif"]


@pytest.mark.parametrize(("status", "payload"), [(404, {}), (200, {}), (200, {"tweet": None})])
async def test_twitter_missing_post_returns_none(
    fetch_api: FetchAPI, status: int, payload: object
) -> None:
    fetch_api.responses["/artist/status/123"] = (status, payload)
    assert await fetch_api.fetcher.twitter("https://x.com/artist/status/123") is None


async def test_twitter_invalid_url_does_not_fetch(fetch_api: FetchAPI) -> None:
    assert await fetch_api.fetcher.twitter("https://x.com/artist") is None
    assert fetch_api.requests == []


@pytest.mark.parametrize("sensitive", [False, True, None])
async def test_twitter_nsfw_uses_post_flag(fetch_api: FetchAPI, sensitive: bool | None) -> None:
    post = (
        None if sensitive is None else TwitterPost(**twitter_payload(possibly_sensitive=sensitive))
    )
    with patch.object(fetch_api.fetcher, "twitter", AsyncMock(return_value=post)):
        assert await fetch_api.fetcher.twitter_is_nsfw("https://x.com/artist/status/123") is bool(
            sensitive
        )


@pytest.mark.parametrize("media", [{}, {"all": []}])
def test_twitter_missing_media_defaults_empty(media: object) -> None:
    assert TwitterPost(**twitter_payload(media=media)).medias == []


def test_twitter_omitted_media_defaults_empty() -> None:
    payload = twitter_payload()
    del payload["media"]
    assert TwitterPost(**payload).medias == []


async def test_bluesky_fetches_json_and_preserves_post(fetch_api: FetchAPI) -> None:
    fetch_api.responses["/profile/artist.test/post/123/json"] = (
        200,
        {"thread": {"post": bluesky_payload()}},
    )
    post = await fetch_api.fetcher.bluesky("https://bsky.app/profile/artist.test/post/123")
    assert post is not None
    assert post.record.text == "A Bluesky post"
    assert fetch_api.requests[0][2]["User-Agent"] == "EmbedFixer/1.0"
    assert fetch_api.urls == ["https://bskx.app/profile/artist.test/post/123/json"]
    assert post.author_md == "[Artist (@artist.test)](<https://bsky.app/profile/artist.test>)"


@pytest.mark.parametrize(("status", "payload"), [(503, {}), (200, {}), (200, {"thread": {}})])
async def test_bluesky_missing_post_returns_none(
    fetch_api: FetchAPI, status: int, payload: object
) -> None:
    fetch_api.responses["/profile/artist/post/123/json"] = (status, payload)
    assert await fetch_api.fetcher.bluesky("https://bsky.app/profile/artist/post/123") is None


@pytest.mark.parametrize("embed", [None, {}, {"external": {"uri": ""}}])
def test_bluesky_no_media(embed: object) -> None:
    post = BskyPost(**bluesky_payload(embed=embed))
    assert post.media_urls == []
    assert post.video_url is None


def test_bluesky_collects_images_video_and_external_gif() -> None:
    post = BskyPost(
        **bluesky_payload(
            embed={
                "images": [{"fullsize": "https://image", "thumb": "https://thumb"}],
                "cid": "video-cid",
                "external": {"uri": "https://gif"},
            }
        )
    )
    video = "https://bsky.social/xrpc/com.atproto.sync.getBlob?cid=video-cid&did=did:plc:artist"
    assert post.video_url == video
    assert post.media_urls == ["https://image", video, "https://gif"]


async def test_kemono_selects_supported_attachments(fetch_api: FetchAPI) -> None:
    names = ["clip.mp4", "one.jpg", "two.jpeg", "three.png", "loop.gif", "ignored.zip"]
    fetch_api.responses["/api/v1/patreon/user/1/post/2"] = (
        200,
        {"post": {"attachments": [{"name": name, "path": f"/{name}"} for name in names]}},
    )
    urls = await fetch_api.fetcher.kemono("https://kemono.su/patreon/user/1/post/2")
    assert fetch_api.urls == ["https://kemono.su/api/v1/patreon/user/1/post/2"]
    assert urls == [
        "https://n1.kemono.su/data/clip.mp4",
        "https://img.kemono.su/thumbnail/data/one.jpg",
        "https://img.kemono.su/thumbnail/data/two.jpeg",
        "https://img.kemono.su/thumbnail/data/three.png",
        "https://n3.kemono.su/data/loop.gif?f=loop.gif",
    ]


@pytest.mark.parametrize("payload", [{}, {"post": {}}, {"post": {"attachments": []}}])
async def test_kemono_missing_attachments(fetch_api: FetchAPI, payload: object) -> None:
    fetch_api.responses["/api/v1/patreon/user/1/post/2"] = (200, payload)
    assert await fetch_api.fetcher.kemono("https://kemono.su/patreon/user/1/post/2") == []


async def test_instagram_fetches_with_url_query(fetch_api: FetchAPI) -> None:
    fetch_api.responses["/api/media"] = (
        200,
        {
            "media": [{"type": "image", "url": "https://image"}],
            "caption": "first\r\nsecond\rthird",
            "author": {"username": "artist", "name": "Artist"},
        },
    )
    url = "https://www.instagram.com/p/123/?img_index=2"
    post = await fetch_api.fetcher.instagram(url)
    assert post is not None
    assert post.caption == "first\nsecond\nthird"
    assert post.media[0].url == "https://image"
    assert post.author_md == "[Artist (@artist)](<https://www.instagram.com/artist/>)"
    assert fetch_api.requests[0][1] == {"url": url}
    assert fetch_api.urls == ["https://fxig.seria.moe/api/media"]


async def test_instagram_non_200_returns_none(fetch_api: FetchAPI) -> None:
    fetch_api.responses["/api/media"] = (429, {})
    assert await fetch_api.fetcher.instagram("https://instagram.com/p/123") is None


@pytest.mark.parametrize(
    ("author", "expected"),
    [
        (None, ""),
        ({"username": "artist"}, "[artist (@artist)](<https://www.instagram.com/artist/>)"),
        (
            {"username": "artist", "name": ""},
            "[artist (@artist)](<https://www.instagram.com/artist/>)",
        ),
    ],
)
def test_instagram_optional_author_and_caption(author: object, expected: str) -> None:
    post = InstagramPost.model_validate({"media": [], "author": author, "caption": None})
    assert post.author_md == expected
    assert post.caption is None


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (PixivArtwork, {}),
        (TwitterPost, {"text": "missing author"}),
        (BskyPost, {"cid": "missing author"}),
        (InstagramPost, {"media": [{"type": "image"}]}),
        (UgoiraMeta, {"src": "missing original"}),
    ],
)
def test_platform_models_reject_incomplete_payloads(
    model: type, payload: dict[str, object]
) -> None:
    with pytest.raises(ValidationError):
        model(**payload)
