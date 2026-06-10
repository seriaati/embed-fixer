from __future__ import annotations

import asyncio
import io
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
    def _zip_to_mp4(zip_bytes: bytes, frames: list[UgoiraFrame]) -> bytes | None:
        with tempfile.TemporaryDirectory() as tmp:
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                zf.extractall(tmp)

            concat_path = f"{tmp}/concat.txt"
            with open(concat_path, "w") as f:
                for frame in frames:
                    f.write(f"file '{tmp}/{frame.file}'\nduration {frame.delay / 1000}\n")
                f.write(f"file '{tmp}/{frames[-1].file}'\n")

            output_path = f"{tmp}/output.mp4"
            try:
                # (
                #     ffmpeg
                #     .input(concat_path, format="concat", safe=0)
                #     .output(output_path, vcodec="libx264", pix_fmt="yuv420p", an=None)
                #     .overwrite_output()
                #     .run(quiet=True)
                # )
                (
                    ffmpeg.input(concat_path, format="concat", safe=0)
                    .output(output_path, vcodec="libx264", pix_fmt="yuv420p", movflags="faststart")
                    .global_args("-an")
                    .overwrite_output()
                    .run(quiet=True)
                )
            except ffmpeg.Error as e:
                logger.error(f"ffmpeg error: {e.stderr}")
                return None

            with open(output_path, "rb") as f:
                return f.read()

    async def _download_ugoira(
        self, meta: UgoiraMeta, *, spoiler: bool, filesize_limit: int
    ) -> None:
        original_bytes, src_bytes = await asyncio.gather(
            self._fetch_bytes(meta.original_src), self._fetch_bytes(meta.src)
        )

        loop = asyncio.get_running_loop()
        for zip_bytes in (original_bytes, src_bytes):
            if zip_bytes is None:
                continue
            mp4_bytes = await loop.run_in_executor(None, self._zip_to_mp4, zip_bytes, meta.frames)
            if mp4_bytes and len(mp4_bytes) <= filesize_limit:
                logger.debug(
                    f"Using ugoira ZIP: {'originalSrc' if zip_bytes is original_bytes else 'src'}"
                )
                self.files["ugoira"] = discord.File(
                    io.BytesIO(mp4_bytes), filename="ugoira.mp4", spoiler=spoiler
                )
                return

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

        # if len(data) > filesize_limit:
        #     data = await asyncio.get_running_loop().run_in_executor(
        #         None, self._downscale_image, data, filesize_limit
        #     )
        #     if data is None:
        #         return

        if media_type:
            filename = f"{url.rsplit('/', maxsplit=1)[-1].split('.', maxsplit=1)[0]}.{media_type.split('/')[-1]}"
        else:
            filename = url.rsplit("/", maxsplit=1)[-1]

        self.files[url] = discord.File(io.BytesIO(data), filename=filename, spoiler=spoiler)

    @staticmethod
    def _downscale_image(data: bytes, filesize_limit: int) -> bytes | None:
        from PIL import Image

        img = Image.open(io.BytesIO(data))
        fmt = img.format or "JPEG"

        for scale in (0.9, 0.8, 0.7):
            new_size = (int(img.width * scale), int(img.height * scale))
            resized = img.resize(new_size, Image.LANCZOS)
            output = io.BytesIO()
            resized.save(output, format=fmt)
            result = output.getvalue()
            if len(result) <= filesize_limit:
                return result

        return None

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
