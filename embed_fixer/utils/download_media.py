from __future__ import annotations

import asyncio
import io
import pathlib
import tempfile
import zipfile
from typing import TYPE_CHECKING

import aiohttp
import discord
import ffmpeg
from loguru import logger

if TYPE_CHECKING:
    from collections.abc import Sequence

    from embed_fixer.utils.fetch_info import UgoiraFrame, UgoiraMeta


class MediaDownloader:
    def __init__(
        self,
        session: aiohttp.ClientSession,
        *,
        media_urls: Sequence[str],
        headers: dict[str, str] | None = None,
        proxy: str | None = None,
        ugoira_meta: UgoiraMeta | None = None,
    ) -> None:
        self.media_urls = media_urls
        self.session = session
        self.headers = headers or {}
        self.files: dict[str, discord.File] = {}
        self.proxy = proxy
        self.ugoira_meta = ugoira_meta
        self.ugoira_file: discord.File | None = None

    async def _fetch_bytes(self, url: str) -> bytes | None:
        timeout = aiohttp.ClientTimeout(total=30)
        try:
            async with self.session.get(
                url, timeout=timeout, headers=self.headers, proxy=self.proxy
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"Failed to fetch {url}, status: {resp.status}")
                    return None
                return await resp.read()
        except Exception:
            logger.exception(f"Failed to fetch bytes from {url}")
            return None

    @staticmethod
    def _zip_to_mp4(zip_bytes: bytes, frames: Sequence[UgoiraFrame]) -> bytes | None:
        """Convert an ugoira frame ZIP into an MP4, returning its bytes (or None on failure)."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = pathlib.Path(tmp)
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                zf.extractall(tmp_dir)

            # ffmpeg concat demuxer: each frame held for its delay, last frame repeated so
            # its duration is honored.
            concat_path = tmp_dir / "concat.txt"
            lines = [
                f"file '{tmp_dir / frame.file}'\nduration {frame.delay / 1000}\n"
                for frame in frames
            ]
            lines.append(f"file '{tmp_dir / frames[-1].file}'\n")
            concat_path.write_text("".join(lines), encoding="utf-8")

            output_path = tmp_dir / "output.mp4"
            try:
                (
                    ffmpeg.input(str(concat_path), format="concat", safe=0)
                    .output(
                        str(output_path),
                        vcodec="libx264",
                        pix_fmt="yuv420p",
                        movflags="faststart",
                        # libx264 + yuv420p requires even dimensions; round down to nearest even.
                        vf="scale=trunc(iw/2)*2:trunc(ih/2)*2",
                    )
                    .global_args("-an")
                    .overwrite_output()
                    .run(quiet=True)
                )
            except ffmpeg.Error as e:
                logger.error(f"ffmpeg failed to convert ugoira: {e.stderr}")
                return None
            except Exception:
                # e.g. the ffmpeg binary is not installed; degrade instead of crashing.
                logger.exception("Failed to convert ugoira to MP4")
                return None

            return output_path.read_bytes()

    async def _download_ugoira(
        self, meta: UgoiraMeta, *, spoiler: bool, filesize_limit: int
    ) -> None:
        """Download an ugoira ZIP and convert it to MP4, preferring the higher resolution.

        Tries the original-resolution ZIP first; if it is unavailable or its MP4 exceeds the
        upload limit, falls back to the smaller 600x600 source.
        """
        loop = asyncio.get_running_loop()
        for label, src in (("originalSrc", meta.original_src), ("src", meta.src)):
            zip_bytes = await self._fetch_bytes(src)
            if zip_bytes is None:
                continue

            mp4_bytes = await loop.run_in_executor(None, self._zip_to_mp4, zip_bytes, meta.frames)
            if mp4_bytes is not None and len(mp4_bytes) <= filesize_limit:
                logger.debug(f"Using ugoira source: {label}")
                self.ugoira_file = discord.File(
                    io.BytesIO(mp4_bytes), filename="ugoira.mp4", spoiler=spoiler
                )
                return

        logger.warning("Failed to produce an ugoira MP4 within the filesize limit")

    async def _download(self, url: str, *, spoiler: bool, filesize_limit: int) -> None:
        timeout = aiohttp.ClientTimeout(total=10)

        try:
            async with self.session.get(
                url, timeout=timeout, headers=self.headers, proxy=self.proxy
            ) as resp:
                if resp.status != 200:
                    return

                content_length = resp.headers.get("Content-Length")
                if content_length is not None and int(content_length) > filesize_limit:
                    return

                data = await resp.read()

                media_type = resp.headers.get("Content-Type")
        except TimeoutError:
            logger.warning(f"Timeout downloading media {url}")
            return
        except Exception:
            logger.exception(f"Failed to download media {url}")
            return

        if media_type:
            filename = f"{url.rsplit('/', maxsplit=1)[-1].split('.', maxsplit=1)[0]}.{media_type.split('/')[-1]}"
        else:
            filename = url.rsplit("/", maxsplit=1)[-1]

        self.files[url] = discord.File(io.BytesIO(data), filename=filename, spoiler=spoiler)

    async def start(self, *, spoiler: bool, filesize_limit: int) -> None:
        async with asyncio.TaskGroup() as tg:
            for media_url in self.media_urls:
                tg.create_task(
                    self._download(media_url, spoiler=spoiler, filesize_limit=filesize_limit)
                )
            if self.ugoira_meta is not None:
                tg.create_task(
                    self._download_ugoira(
                        self.ugoira_meta, spoiler=spoiler, filesize_limit=filesize_limit
                    )
                )
