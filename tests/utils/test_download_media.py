from __future__ import annotations

import asyncio
import io
import shutil
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import ffmpeg
import pytest
import pytest_asyncio
from aiohttp import web
from aiohttp_client_cache import CacheBackend, CachedSession
from PIL import Image

from embed_fixer.utils.download_media import MediaDownloader
from embed_fixer.utils.fetch_info import UgoiraFrame, UgoiraMeta

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from aiohttp.pytest_plugin import AiohttpServer
    from aiohttp.test_utils import TestServer


@pytest_asyncio.fixture
async def media_server(aiohttp_server: AiohttpServer) -> tuple[TestServer, list[web.Request]]:
    requests: list[web.Request] = []

    async def respond(request: web.Request) -> web.StreamResponse:
        requests.append(request)
        if request.path == "/missing":
            return web.Response(status=404)
        if request.path in {"/stream", "/chunked.png"}:
            response = web.StreamResponse(headers={"Content-Type": "image/png"})
            await response.prepare(request)
            chunks = (b"streamed image",) if request.path == "/stream" else (b"x" * 65_536, b"x")
            for chunk in chunks:
                await response.write(chunk)
            await response.write_eof()
            return response
        if request.path == "/large.png":
            return web.Response(body=b"x" * 101, content_type="image/png")
        if request.path == "/raw.data":
            return web.Response(body=b"raw", content_type="application/octet-stream")
        if request.path == "/without-type":
            response = web.StreamResponse()
            response.headers.pop("Content-Type", None)
            await response.prepare(request)
            await response.write(b"no type")
            await response.write_eof()
            return response
        return web.Response(body=b"image", content_type="image/png")

    app = web.Application()
    app.router.add_get("/{path:.*}", respond)
    return await aiohttp_server(app), requests


@pytest_asyncio.fixture(params=[False, True], ids=["plain", "cached"])
async def media_session(request: pytest.FixtureRequest) -> AsyncIterator[aiohttp.ClientSession]:
    client = CachedSession(cache=CacheBackend()) if request.param else aiohttp.ClientSession()
    async with client as session:
        yield session


@pytest.fixture
def ugoira_frames() -> list[UgoiraFrame]:
    return [UgoiraFrame(file="0.png", delay=100), UgoiraFrame(file="1.png", delay=200)]


@pytest.fixture(params=[zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED], ids=["stored", "deflated"])
def ugoira_zip(ugoira_frames: list[UgoiraFrame], request: pytest.FixtureRequest) -> bytes:
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", compression=request.param) as zipped:
        for index, frame in enumerate(ugoira_frames):
            image = io.BytesIO()
            Image.new("RGB", (17, 19), (index * 100, 50, 100)).save(image, format="PNG")
            zipped.writestr(frame.file, image.getvalue())
    return archive.getvalue()


@pytest.fixture
def corrupt_ugoira_zip(ugoira_zip: bytes) -> bytes:
    with zipfile.ZipFile(io.BytesIO(ugoira_zip)) as archive:
        frame = archive.infolist()[0]
    offset = frame.header_offset + 30 + len(frame.filename.encode()) + len(frame.extra)
    corrupted = bytearray(ugoira_zip)
    if frame.compress_type == zipfile.ZIP_DEFLATED:
        corrupted[offset] = (corrupted[offset] & ~7) | 7
    else:
        corrupted[offset] ^= 0xFF
    return bytes(corrupted)


def ugoira_meta(frames: list[UgoiraFrame]) -> UgoiraMeta:
    return UgoiraMeta(
        src="https://small.zip",
        originalSrc="https://large.zip",
        mime_type="image/png",
        frames=frames,
    )


async def test_fetch_bytes_reads_real_body_and_forwards_headers(
    media_session: aiohttp.ClientSession, media_server: tuple[TestServer, list[web.Request]]
) -> None:
    server, requests = media_server
    downloader = MediaDownloader(
        media_session, media_urls=[], headers={"Referer": "https://pixiv.net"}
    )
    assert await downloader._fetch_bytes(str(server.make_url("/raw.data"))) == b"raw"
    assert requests[0].headers["Referer"] == "https://pixiv.net"


async def test_fetch_bytes_non_200(
    media_session: aiohttp.ClientSession, media_server: tuple[TestServer, list[web.Request]]
) -> None:
    server, _ = media_server
    downloader = MediaDownloader(media_session, media_urls=[])
    assert await downloader._fetch_bytes(str(server.make_url("/missing"))) is None


async def test_cached_file_downloads_preserve_other_requests_cache(
    media_server: tuple[TestServer, list[web.Request]],
) -> None:
    server, requests = media_server
    metadata_url = str(server.make_url("/raw.data"))
    image_url = str(server.make_url("/image.jpg"))
    async with CachedSession(cache=CacheBackend()) as session:
        downloader = MediaDownloader(session, media_urls=[])
        assert await downloader._fetch_bytes(metadata_url) == b"raw"
        file = await downloader._fetch_file(image_url, spoiler=False, filesize_limit=100)
        assert file is not None
        assert file.fp.read() == b"image"
        file.close()
        async with session.get(image_url) as response:
            assert await response.read() == b"image"
        file = await downloader._fetch_file(image_url, spoiler=False, filesize_limit=100)
        assert file is not None
        assert file.fp.read() == b"image"
        file.close()
        async with session.get(image_url) as response:
            assert await response.read() == b"image"
        assert await downloader._fetch_bytes(metadata_url) == b"raw"
    assert [request.path for request in requests] == [
        "/raw.data",
        "/image.jpg",
        "/image.jpg",
        "/image.jpg",
    ]


@pytest.mark.parametrize("failure", [TimeoutError(), aiohttp.ClientConnectionError("closed")])
async def test_fetch_bytes_transport_errors(
    media_session: aiohttp.ClientSession, failure: Exception
) -> None:
    downloader = MediaDownloader(media_session, media_urls=[], proxy="http://proxy.invalid")
    with patch.object(media_session, "get", side_effect=failure) as get:
        assert await downloader._fetch_bytes("https://media.invalid/file") is None
    assert get.call_args.kwargs["timeout"].total == 30
    assert get.call_args.kwargs["proxy"] == "http://proxy.invalid"


@pytest.mark.parametrize(
    ("path", "filename", "expected"),
    [
        ("/image.jpg", "image.png", b"image"),
        ("/raw.data", "raw.data", b"raw"),
        ("/without-type", "without-type", b"no type"),
        ("/stream", "stream.png", b"streamed image"),
    ],
)
async def test_fetch_file_body_filename_and_spoiler(
    media_session: aiohttp.ClientSession,
    media_server: tuple[TestServer, list[web.Request]],
    path: str,
    filename: str,
    expected: bytes,
) -> None:
    server, requests = media_server
    downloader = MediaDownloader(
        media_session, media_urls=[], headers={"Referer": "https://pixiv.net"}
    )
    result = await downloader._fetch_file(
        str(server.make_url(path)), spoiler=True, filesize_limit=100
    )
    assert result is not None
    assert result.filename == f"SPOILER_{filename}"
    assert result.spoiler
    assert result.fp.read() == expected
    assert requests[0].headers["Referer"] == "https://pixiv.net"
    result.close()


@pytest.mark.parametrize("path", ["/missing", "/large.png"])
async def test_fetch_file_rejects_failed_or_oversized_response(
    media_session: aiohttp.ClientSession,
    media_server: tuple[TestServer, list[web.Request]],
    path: str,
) -> None:
    server, _ = media_server
    downloader = MediaDownloader(media_session, media_urls=[])
    assert (
        await downloader._fetch_file(str(server.make_url(path)), spoiler=False, filesize_limit=100)
        is None
    )


@pytest.mark.parametrize(
    ("path", "expected"),
    [("/image.jpg", b"image"), ("/stream", b"streamed image"), ("/chunked.png", b"x" * 65_537)],
)
async def test_fetch_file_accepts_exact_limit(
    media_session: aiohttp.ClientSession,
    media_server: tuple[TestServer, list[web.Request]],
    path: str,
    expected: bytes,
) -> None:
    server, _ = media_server
    downloader = MediaDownloader(media_session, media_urls=[])
    result = await downloader._fetch_file(
        str(server.make_url(path)), spoiler=False, filesize_limit=len(expected)
    )
    assert result is not None
    assert result.fp.read() == expected
    result.close()


@pytest.mark.parametrize(("path", "filesize_limit"), [("/stream", 3), ("/chunked.png", 65_536)])
async def test_fetch_file_rejects_oversized_chunked_response(
    media_session: aiohttp.ClientSession,
    media_server: tuple[TestServer, list[web.Request]],
    path: str,
    filesize_limit: int,
) -> None:
    server, _ = media_server
    downloader = MediaDownloader(media_session, media_urls=[])
    result = await downloader._fetch_file(
        str(server.make_url(path)), spoiler=False, filesize_limit=filesize_limit
    )
    try:
        assert result is None
    finally:
        if result is not None:
            result.close()


@pytest.mark.parametrize("declared_length", [False, True])
async def test_fetch_file_rejects_oversized_response_before_body_finishes(
    media_session: aiohttp.ClientSession, aiohttp_server: AiohttpServer, declared_length: bool
) -> None:
    finish_response = asyncio.Event()

    async def respond(request: web.Request) -> web.StreamResponse:
        response = web.StreamResponse(headers={"Content-Type": "image/png"})
        if declared_length:
            response.content_length = 101
        await response.prepare(request)
        if not declared_length:
            await response.write(b"x" * 64)
            await response.write(b"x" * 37)
        await finish_response.wait()
        return response

    app = web.Application()
    app.router.add_get("/oversized.png", respond)
    server = await aiohttp_server(app)
    downloader = MediaDownloader(media_session, media_urls=[])
    try:
        result = await asyncio.wait_for(
            downloader._fetch_file(
                str(server.make_url("/oversized.png")), spoiler=False, filesize_limit=100
            ),
            timeout=1,
        )
        assert result is None
    finally:
        finish_response.set()


@pytest.mark.parametrize("failure", [TimeoutError(), aiohttp.ClientConnectionError("closed")])
async def test_fetch_file_transport_errors(
    media_session: aiohttp.ClientSession, failure: Exception
) -> None:
    downloader = MediaDownloader(media_session, media_urls=[], proxy="http://proxy.invalid")
    with patch.object(media_session, "get", side_effect=failure) as get:
        assert (
            await downloader._fetch_file(
                "https://media.invalid/file", spoiler=False, filesize_limit=100
            )
            is None
        )
    assert get.call_args.kwargs["timeout"].total == 10
    assert get.call_args.kwargs["proxy"] == "http://proxy.invalid"


@pytest.mark.parametrize("original_path", ["/missing", "/large.png", "/chunked.png"])
async def test_download_falls_back_and_keys_by_original_url(
    media_session: aiohttp.ClientSession,
    media_server: tuple[TestServer, list[web.Request]],
    original_path: str,
) -> None:
    server, requests = media_server
    original = str(server.make_url(original_path))
    fallback = str(server.make_url("/image.jpg"))
    downloader = MediaDownloader(
        media_session, media_urls=[original], fallback_urls={original: fallback}
    )
    await downloader.start(spoiler=False, filesize_limit=100)
    assert list(downloader.files) == [original]
    assert downloader.files[original].fp.read() == b"image"
    assert [request.path for request in requests] == [original_path, "/image.jpg"]
    downloader.files[original].close()


async def test_download_keeps_original_when_it_fits(
    media_session: aiohttp.ClientSession, media_server: tuple[TestServer, list[web.Request]]
) -> None:
    server, requests = media_server
    original = str(server.make_url("/raw.data"))
    fallback = str(server.make_url("/image.jpg"))
    downloader = MediaDownloader(
        media_session, media_urls=[original], fallback_urls={original: fallback}
    )
    await downloader.start(spoiler=False, filesize_limit=100)
    assert len(requests) == 1
    assert downloader.files[original].filename == "raw.data"
    downloader.files[original].close()


async def test_download_all_candidates_fail(
    media_session: aiohttp.ClientSession, media_server: tuple[TestServer, list[web.Request]]
) -> None:
    server, requests = media_server
    original = str(server.make_url("/large.png"))
    downloader = MediaDownloader(
        media_session,
        media_urls=[original],
        fallback_urls={original: str(server.make_url("/missing"))},
    )
    await downloader.start(spoiler=False, filesize_limit=100)
    assert downloader.files == {}
    assert len(requests) == 2


def test_ugoira_empty_frames_returns_none() -> None:
    assert MediaDownloader._zip_to_mp4(b"", []) is None


def test_ugoira_concat_and_encoder_arguments(
    ugoira_zip: bytes, ugoira_frames: list[UgoiraFrame]
) -> None:
    graph = MagicMock()
    graph.output.return_value = graph
    graph.global_args.return_value = graph
    graph.overwrite_output.return_value = graph
    captured: list[str] = []

    def encode(*, quiet: bool) -> None:
        assert quiet
        output = Path(graph.output.call_args.args[0])
        concat = Path(graph.input_path)
        captured.append(concat.read_text(encoding="utf-8"))
        assert (output.parent / "0.png").read_bytes().startswith(b"\x89PNG")
        assert (output.parent / "1.png").is_file()
        output.write_bytes(b"encoded mp4")

    def input_graph(filename: str, **kwargs: Any) -> MagicMock:
        assert kwargs == {"format": "concat", "safe": 0}
        graph.input_path = filename
        return graph

    graph.run.side_effect = encode
    with patch("embed_fixer.utils.download_media.ffmpeg.input", side_effect=input_graph):
        result = MediaDownloader._zip_to_mp4(ugoira_zip, ugoira_frames)
    assert result == b"encoded mp4"
    assert "0.png'\nduration 0.1\n" in captured[0]
    assert "1.png'\nduration 0.2\n" in captured[0]
    assert captured[0].endswith("1.png'\n")
    assert captured[0].count("1.png") == 2
    assert graph.output.call_args.kwargs == {
        "vcodec": "libx264",
        "pix_fmt": "yuv420p",
        "movflags": "faststart",
        "vf": "scale=trunc(iw/2)*2:trunc(ih/2)*2",
    }
    graph.global_args.assert_called_once_with("-an")
    assert not Path(graph.input_path).exists()


@pytest.mark.skipif(
    shutil.which("ffmpeg") is None,
    reason="ffmpeg is unavailable; encoder boundary and concat are covered separately",
)
def test_ugoira_real_zip_converts_to_decodable_even_sized_mp4(
    ugoira_zip: bytes, ugoira_frames: list[UgoiraFrame], tmp_path: Path
) -> None:
    encoded = MediaDownloader._zip_to_mp4(ugoira_zip, ugoira_frames)
    assert encoded is not None
    output = tmp_path / "ugoira.mp4"
    output.write_bytes(encoded)
    probe = ffmpeg.probe(str(output))
    video = next(stream for stream in probe["streams"] if stream["codec_type"] == "video")
    assert video["codec_name"] == "h264"
    assert (video["width"], video["height"]) == (16, 18)
    assert float(probe["format"]["duration"]) >= 0.3
    assert all(stream["codec_type"] != "audio" for stream in probe["streams"])
    _, stderr = (
        ffmpeg.input(str(output))
        .output("pipe:", format="null")
        .global_args("-v", "error", "-xerror")
        .run(capture_stdout=True, capture_stderr=True)
    )
    assert stderr == b""


@pytest.mark.parametrize(
    "failure", [ffmpeg.Error("ffmpeg", b"stdout", b"invalid input"), FileNotFoundError("ffmpeg")]
)
def test_ugoira_encoder_failure_returns_none(
    ugoira_zip: bytes, ugoira_frames: list[UgoiraFrame], failure: Exception
) -> None:
    with patch("ffmpeg._run.subprocess.Popen", side_effect=failure):
        assert MediaDownloader._zip_to_mp4(ugoira_zip, ugoira_frames) is None


def test_ugoira_invalid_zip_degrades_to_none(ugoira_frames: list[UgoiraFrame]) -> None:
    assert MediaDownloader._zip_to_mp4(b"not a zip", ugoira_frames) is None


def test_ugoira_corrupt_member_degrades_to_none(
    corrupt_ugoira_zip: bytes, ugoira_frames: list[UgoiraFrame]
) -> None:
    assert MediaDownloader._zip_to_mp4(corrupt_ugoira_zip, ugoira_frames) is None


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is unavailable")
async def test_ugoira_corrupt_original_falls_back_to_real_conversion(
    media_session: aiohttp.ClientSession,
    aiohttp_server: AiohttpServer,
    corrupt_ugoira_zip: bytes,
    ugoira_zip: bytes,
    ugoira_frames: list[UgoiraFrame],
) -> None:
    requests: list[str] = []

    async def respond(request: web.Request) -> web.Response:
        await request.read()
        requests.append(request.path)
        if request.path == "/original.zip":
            return web.Response(body=corrupt_ugoira_zip, content_type="application/zip")
        if request.path == "/fallback.zip":
            return web.Response(body=ugoira_zip, content_type="application/zip")
        return web.Response(body=b"image", content_type="image/png")

    app = web.Application()
    app.router.add_get("/{path:.*}", respond)
    server = await aiohttp_server(app)
    image_url = str(server.make_url("/image.png"))
    meta = UgoiraMeta(
        src=str(server.make_url("/fallback.zip")),
        originalSrc=str(server.make_url("/original.zip")),
        mime_type="image/png",
        frames=ugoira_frames,
    )
    downloader = MediaDownloader(media_session, media_urls=[image_url], ugoira_meta=meta)
    await downloader.start(spoiler=False, filesize_limit=100_000)
    assert downloader.files[image_url].fp.read() == b"image"
    assert downloader.ugoira_file is not None
    assert [path for path in requests if path.endswith(".zip")] == [
        "/original.zip",
        "/fallback.zip",
    ]
    _, stderr = (
        ffmpeg.input("pipe:")
        .output("pipe:", format="null")
        .global_args("-v", "error", "-xerror")
        .run(input=downloader.ugoira_file.fp.read(), capture_stdout=True, capture_stderr=True)
    )
    assert stderr == b""
    downloader.files[image_url].close()
    downloader.ugoira_file.close()


@pytest.mark.parametrize(
    ("fetched", "encoded", "expected_calls"),
    [
        ([b"original"], [b"mp4"], 1),
        ([None, b"small"], [b"mp4"], 2),
        ([b"large", b"small"], [b"x" * 101, b"mp4"], 2),
        ([b"invalid", b"small"], [None, b"mp4"], 2),
    ],
)
async def test_ugoira_prefers_original_then_falls_back(
    media_session: aiohttp.ClientSession,
    ugoira_frames: list[UgoiraFrame],
    fetched: list[bytes | None],
    encoded: list[bytes | None],
    expected_calls: int,
) -> None:
    meta = ugoira_meta(ugoira_frames)
    downloader = MediaDownloader(media_session, media_urls=[], ugoira_meta=meta)
    with (
        patch.object(downloader, "_fetch_bytes", AsyncMock(side_effect=fetched)) as fetch,
        patch.object(downloader, "_zip_to_mp4", side_effect=encoded) as convert,
    ):
        await downloader.start(spoiler=True, filesize_limit=100)
    assert fetch.await_count == expected_calls
    assert fetch.await_args_list[0].args == ("https://large.zip",)
    if expected_calls == 2:
        assert fetch.await_args_list[1].args == ("https://small.zip",)
    assert convert.call_count == len(encoded)
    assert downloader.ugoira_file is not None
    assert downloader.ugoira_file.filename == "SPOILER_ugoira.mp4"
    assert downloader.ugoira_file.fp.read() == b"mp4"
    assert downloader.files == {}
    downloader.ugoira_file.close()


@pytest.mark.parametrize(
    ("fetched", "encoded"),
    [
        ([None, None], []),
        ([b"large", b"small"], [None, None]),
        ([b"large", b"small"], [b"x" * 101, b"x" * 101]),
    ],
)
async def test_ugoira_all_sources_fail(
    media_session: aiohttp.ClientSession,
    ugoira_frames: list[UgoiraFrame],
    fetched: list[bytes | None],
    encoded: list[bytes | None],
) -> None:
    downloader = MediaDownloader(
        media_session, media_urls=[], ugoira_meta=ugoira_meta(ugoira_frames)
    )
    with (
        patch.object(downloader, "_fetch_bytes", AsyncMock(side_effect=fetched)),
        patch.object(downloader, "_zip_to_mp4", side_effect=encoded),
    ):
        await downloader.start(spoiler=False, filesize_limit=100)
    assert downloader.ugoira_file is None


async def test_start_downloads_images_and_ugoira_together(
    media_session: aiohttp.ClientSession,
    media_server: tuple[TestServer, list[web.Request]],
    ugoira_frames: list[UgoiraFrame],
) -> None:
    server, _ = media_server
    url = str(server.make_url("/image.jpg"))
    downloader = MediaDownloader(
        media_session, media_urls=[url], ugoira_meta=ugoira_meta(ugoira_frames)
    )
    with (
        patch.object(downloader, "_fetch_bytes", AsyncMock(return_value=b"zip")),
        patch.object(downloader, "_zip_to_mp4", return_value=b"mp4"),
    ):
        await downloader.start(spoiler=False, filesize_limit=100)
    assert downloader.files[url].fp.read() == b"image"
    assert downloader.ugoira_file is not None
    assert downloader.ugoira_file.fp.read() == b"mp4"
    downloader.files[url].close()
    downloader.ugoira_file.close()


async def test_ugoira_accepts_exact_upload_limit(
    media_session: aiohttp.ClientSession, ugoira_frames: list[UgoiraFrame]
) -> None:
    downloader = MediaDownloader(
        media_session, media_urls=[], ugoira_meta=ugoira_meta(ugoira_frames)
    )
    with (
        patch.object(downloader, "_fetch_bytes", AsyncMock(return_value=b"zip")) as fetch,
        patch.object(downloader, "_zip_to_mp4", return_value=b"mp4"),
    ):
        await downloader.start(spoiler=False, filesize_limit=3)
    assert fetch.await_count == 1
    assert downloader.ugoira_file is not None
    assert downloader.ugoira_file.fp.read() == b"mp4"
    downloader.ugoira_file.close()


def test_ugoira_missing_frame_degrades_to_none(ugoira_zip: bytes) -> None:
    frames = [UgoiraFrame(file="missing.png", delay=100)]
    assert MediaDownloader._zip_to_mp4(ugoira_zip, frames) is None
