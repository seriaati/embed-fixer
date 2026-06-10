from __future__ import annotations

import asyncio
import io
from typing import TYPE_CHECKING

import aiohttp
import discord
from loguru import logger

if TYPE_CHECKING:
    from collections.abc import Sequence


class MediaDownloader:
    def __init__(
        self,
        session: aiohttp.ClientSession,
        *,
        media_urls: Sequence[str],
        headers: dict[str, str] | None = None,
        proxy: str | None = None,
    ) -> None:
        self.media_urls = media_urls
        self.session = session
        self.headers = headers or {}
        self.files: dict[str, discord.File] = {}
        self.proxy = proxy

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

    async def _download_ugoira(self, meta: UgoiraMeta, *, spoiler: bool, filesize_limit: int) -> None:
        # 1. Fetch both ZIPs in parallel
        original_bytes, src_bytes = await asyncio.gather(
            self._fetch_bytes(meta.original_src),
            self._fetch_bytes(meta.src),
        )

        # 2. Try originalSrc first, fall back to src
        for zip_bytes in (original_bytes, src_bytes):
            if zip_bytes is None:
                continue
            mp4_bytes = await asyncio.get_event_loop().run_in_executor(
                None, self._zip_to_mp4, zip_bytes, meta.frames
            )
            if mp4_bytes and len(mp4_bytes) <= filesize_limit:
                self.files["ugoira"] = discord.File(
                    io.BytesIO(mp4_bytes), filename="ugoira.mp4", spoiler=spoiler
                )
                return

    async def start(self, *, spoiler: bool, filesize_limit: int) -> None:
        async with asyncio.TaskGroup() as tg:
            for media_url in self.media_urls:
                tg.create_task(
                    self._download(media_url, spoiler=spoiler, filesize_limit=filesize_limit)
                )
