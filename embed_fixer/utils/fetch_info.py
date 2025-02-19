from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final

from embed_fixer.models import BlueskyPostInfo, PixivArtworkInfo, TwitterPostInfo

if TYPE_CHECKING:
    import aiohttp

PIXIV_R18_TAG: Final[str] = "#R-18"


class PostInfoFetcher:  # noqa: B903
    def __init__(self, session: aiohttp.ClientSession) -> None:
        self.session = session

    async def pixiv(self, url: str) -> PixivArtworkInfo | None:
        artwork_id = url.split("/")[-1]
        api_url = f"https://phixiv.net/api/info?id={artwork_id}"
        async with self.session.get(api_url) as response:
            if response.status != 200:
                return None

            data = await response.json()

        if "image_proxy_urls" not in data:
            return None

        return PixivArtworkInfo(
            tags=data.get("tags", []),
            image_urls=data["image_proxy_urls"],
            description=data.get("description", ""),
            author_name=data.get("author_name", ""),
            author_id=data.get("author_id", ""),
        )

    async def is_artwork_nsfw(self, url: str) -> bool:
        artwork_info = await self.pixiv(url)
        if artwork_info is None:
            return False
        return PIXIV_R18_TAG in artwork_info.tags

    async def twitter(self, url: str) -> TwitterPostInfo | None:
        if "twitter.com" in url:
            api_url = url.replace("twitter.com", "api.fxtwitter.com")
        else:
            api_url = url.replace("x.com", "api.fxtwitter.com")

        allowed_media_types = {"photo", "video", "gif"}
        media_index = None

        if "photo" in api_url or "video" in api_url:
            allowed_media_types = {api_url.split("/")[-2]}
            media_index = int(api_url.split("/")[-1]) - 1
            api_url = "/".join(api_url.split("/")[:-2])

        async with self.session.get(api_url) as response:
            if response.status != 200:
                return None

            data = await response.json()
            tweet = data["tweet"]
            medias = tweet.get("media")
            author = tweet.get("author")
            if medias is None or author is None:
                return None

            urls = [media["url"] for media in medias["all"] if media["type"] in allowed_media_types]
            media_urls = (
                [urls[media_index]] if media_index is not None and len(urls) > media_index else urls
            )
            return TwitterPostInfo(
                media_urls=media_urls,
                content=tweet.get("text", ""),
                author_name=author.get("name", ""),
                author_handle=author.get("screen_name", ""),
            )

    async def bluesky(self, url: str) -> BlueskyPostInfo | None:
        api_url = url.replace("bsky.app", "bskx.app") + "/json"

        async with self.session.get(api_url) as response:
            if response.status != 200:
                return None

            data = await response.json()
            if not data["posts"]:
                return None

            urls: list[str] = []
            post = data["posts"][0]
            embed = post.get("embed")
            author = post.get("author")

            if embed is None or author is None:
                return None

            # Image
            if (images := embed.get("images")) is not None:
                urls.extend(image["fullsize"] for image in images)

            # Video
            if (
                (cid := embed.get("cid")) is not None
                and (author := post.get("author")) is not None
                and (did := author.get("did"))
            ):
                urls.append(
                    f"https://bsky.social/xrpc/com.atproto.sync.getBlob?cid={cid}&did={did}"
                )

            # External GIF
            if (external := (embed.get("external"))) and (uri := external.get("uri")):
                urls.append(uri)

            return BlueskyPostInfo(
                media_urls=urls,
                content=post.get("text", ""),
                author_name=author.get("displayName", ""),
                author_handle=author.get("handle", ""),
            )

    async def kemono(self, url: str) -> list[str]:
        urls: list[str] = []
        api_url = url.replace("kemono.su", "kemono.su/api/v1")

        async with self.session.get(api_url) as resp:
            data = await resp.json()

        if "attachments" not in data:
            return urls

        attachments: list[dict[str, str]] = data["attachments"]
        for attachment in attachments:
            if attachment["name"].endswith(".mp4"):
                urls.append(f"https://n1.kemono.su/data{attachment['path']}")
            elif attachment["name"].endswith((".jpg", ".jpeg", ".png")):
                urls.append(f"https://img.kemono.su/thumbnail/data{attachment['path']}")
            elif attachment["name"].endswith(".gif"):
                urls.append(f"https://n3.kemono.su/data{attachment['path']}?f={attachment['name']}")

        return urls

    async def iwara(self, url: str) -> list[str]:
        match = re.search(r"/video/([a-zA-Z0-9]+)/", url)
        video_id = match.group(1) if match else None
        if video_id is None:
            return []
        return [f"https://fxiwara.seria.moe/dl/{video_id}/360"]
