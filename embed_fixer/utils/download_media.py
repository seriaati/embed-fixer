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
    def __init__(self, session: aiohttp.ClientSession, *, media_urls: Sequence[str]) -> None:
        self.media_urls = media_urls
        self.session = session
        self.files: dict[str, discord.File] = {}

    async def _download(self, url: str, *, spoiler: bool, filesize_limit: int) -> None:
        timeout = aiohttp.ClientTimeout(total=10)

        try:
            async with self.session.get(url, timeout=timeout) as resp:
                if resp.status != 200:
                    return

                content_length = resp.headers.get("Content-Length")
                if content_length is not None and int(content_length) > filesize_limit:
                    return

                data = await resp.read()

                media_type = resp.headers.get("Content-Type")
        except Exception:
            logger.exception(f"Failed to download media {url}")
            return

        if media_type:
            filename = f"{url.split('/')[-1].split('.')[0]}.{media_type.split('/')[-1]}"
        else:
            filename = url.split("/")[-1]

        self.files[url] = discord.File(io.BytesIO(data), filename=filename, spoiler=spoiler)

    async def start(self, *, spoiler: bool, filesize_limit: int) -> None:
        async with asyncio.TaskGroup() as tg:
            for media_url in self.media_urls:
                tg.create_task(
                    self._download(media_url, spoiler=spoiler, filesize_limit=filesize_limit)
                )
