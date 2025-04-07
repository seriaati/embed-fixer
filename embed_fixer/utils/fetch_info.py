from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final

from pydantic import BaseModel, Field, field_validator

from embed_fixer.utils.misc import remove_html_tags, replace_domain

if TYPE_CHECKING:
    import datetime

    import aiohttp

PIXIV_R18_TAG: Final[str] = "#R-18"
TWITTER_MEDIA_TYPES = {"photo", "video", "gif"}


class PostInfoFetcher:  # noqa: B903
    def __init__(self, session: aiohttp.ClientSession) -> None:
        self.session = session

    @staticmethod
    def _extract_pixiv_id(url: str) -> str | None:
        match = re.search(r"pixiv.net(?:/[^/]+)?/artworks/(\d+)", url)
        return match.group(1) if match else None

    @staticmethod
    def _extract_twitter_details(url: str) -> tuple[str, str] | None:
        match = re.search(r"(twitter|x).com/([^/]+)/status/(\d+)", url)
        if match:
            return match.group(1), match.group(2)
        return None

    @staticmethod
    def _extract_tweet_photo_index(url: str) -> int | None:
        match = re.search(r"/photo/(\d+)$", url)
        return int(match.group(1)) - 1 if match else None

    @staticmethod
    def _extract_iwara_id(url: str) -> str | None:
        match = re.search(r"iwara.tv/video/([a-zA-Z0-9]+)", url)
        return match.group(1) if match else None

    @staticmethod
    def _extract_b23_slug(url: str) -> str | None:
        match = re.search(r"b23.tv/([\w]+)", url)
        return match.group(1) if match else None

    @staticmethod
    def _extract_bilibili_id(url: str) -> str | None:
        match = re.search(r"bilibili.com/video/([\w]+)", url)
        return match.group(1) if match else None

    async def pixiv(self, url: str) -> PixivArtwork | None:
        artwork_id = self._extract_pixiv_id(url)
        if artwork_id is None:
            return None

        api_url = f"https://phixiv.net/api/info?id={artwork_id}"
        async with self.session.get(api_url) as response:
            if response.status != 200:
                return None

            data = await response.json()

        return PixivArtwork(**data)

    async def pixiv_is_nsfw(self, url: str) -> bool:
        artwork_info = await self.pixiv(url)
        if artwork_info is None:
            return False
        return PIXIV_R18_TAG in artwork_info.tags

    async def twitter(self, url: str) -> TwitterPost | None:
        ids = self._extract_twitter_details(url)
        if ids is None:
            return None

        handle, tweet_id = ids
        api_url = f"https://api.fxtwitter.com/{handle}/status/{tweet_id}"

        async with self.session.get(api_url) as response:
            if response.status != 200:
                return None

            data = await response.json()

        tweet = data.get("tweet")
        if tweet is None:
            return None

        tweet = TwitterPost(**tweet)
        media_index = self._extract_tweet_photo_index(url)
        if media_index is not None and len(tweet.medias) > media_index:
            tweet.medias = [tweet.medias[media_index]]

        return tweet

    async def bluesky(self, url: str) -> BskyPost | None:
        api_url = replace_domain(url, "bsky.app", "bskx.app") + "/json"

        async with self.session.get(api_url) as response:
            if response.status != 200:
                return None

            data = await response.json()

        if not data.get("posts"):
            return None
        post = data["posts"][0]

        return BskyPost(**post)

    async def kemono(self, url: str) -> list[str]:
        urls: list[str] = []
        api_url = replace_domain(url, "kemono.su", "kemono.su/api/v1")

        async with self.session.get(api_url) as resp:
            data = await resp.json()

        try:
            attachments: list[dict[str, str]] = data["post"]["attachments"]
        except KeyError:
            return []

        for attachment in attachments:
            if attachment["name"].endswith(".mp4"):
                urls.append(f"https://n1.kemono.su/data{attachment['path']}")
            elif attachment["name"].endswith((".jpg", ".jpeg", ".png")):
                urls.append(f"https://img.kemono.su/thumbnail/data{attachment['path']}")
            elif attachment["name"].endswith(".gif"):
                urls.append(f"https://n3.kemono.su/data{attachment['path']}?f={attachment['name']}")

        return urls

    def bilibili(self, url: str) -> list[str]:
        b23_id = self._extract_b23_slug(url)
        if b23_id is not None:
            return [f"https://fxbilibili.seria.moe/dl/b23/{b23_id}"]

        bvid = self._extract_bilibili_id(url)
        if bvid is None:
            return []

        return [f"https://fxbilibili.seria.moe/dl/{bvid}"]


class PixivArtwork(BaseModel):
    image_urls: list[str] = Field(alias="image_proxy_urls", default_factory=list)
    title: str
    ai_generated: bool
    description: str
    tags: list[str]
    url: str
    author_name: str
    author_id: str
    is_ugoira: bool
    created_at: datetime.datetime = Field(alias="create_date")
    profile_image_url: str = Field(alias="user_profile_image_urls")

    @field_validator("description", mode="after")
    @classmethod
    def __format_description(cls, v: str) -> str:
        return remove_html_tags(v.replace("  ", "\n"))

    @property
    def author_md(self) -> str:
        return f"[{self.author_name}](<https://www.pixiv.net/users/{self.author_id}>)"


class TwitterPostMedia(BaseModel):
    type: str
    url: str
    width: int
    height: int


class TwitterPostAuthor(BaseModel):
    id: str
    name: str
    handle: str = Field(alias="screen_name")

    avatar_url: str
    banner_url: str
    url: str


class TwitterPost(BaseModel):
    medias: list[TwitterPostMedia]
    author: TwitterPostAuthor
    text: str

    @field_validator("medias", mode="after")
    @classmethod
    def __format_medias(cls, v: list[TwitterPostMedia]) -> list[TwitterPostMedia]:
        return [media for media in v if media.type in TWITTER_MEDIA_TYPES]

    @property
    def author_md(self) -> str:
        return f"[{self.author.name} (@{self.author.handle})](<{self.author.url}>)"


class BskyPostAuthor(BaseModel):
    did: str
    handle: str
    name: str = Field(alias="displayName")
    avatar_url: str = Field(alias="avatar")


class BskyPostEmbedImage(BaseModel):
    fullsize: str
    thumbnail: str


class BskyPostEmbedExternal(BaseModel):
    uri: str


class BskyPostEmbed(BaseModel):
    images: list[BskyPostEmbedImage] = Field(default_factory=list)
    cid: str | None = None
    external: BskyPostEmbedExternal | None = None


class BskyPostRecord(BaseModel):
    text: str = ""


class BskyPost(BaseModel):
    cid: str
    author: BskyPostAuthor
    embed: BskyPostEmbed | None = None
    record: BskyPostRecord

    @property
    def author_md(self) -> str:
        return f"[{self.author.name} (@{self.author.handle})](<https://bsky.app/profile/{self.author.handle}>)"

    @property
    def video_url(self) -> str | None:
        if self.embed is None or self.embed.cid is None:
            return None

        return f"https://bsky.social/xrpc/com.atproto.sync.getBlob?cid={self.embed.cid}&did={self.author.did}"

    @property
    def media_urls(self) -> list[str]:
        urls: list[str] = []

        if self.embed is None:
            return urls

        # Image
        urls.extend(image.fullsize for image in self.embed.images)

        # Video
        if self.video_url is not None:
            urls.append(self.video_url)

        # External GIF
        if (external := (self.embed.external)) and (uri := external.uri):
            urls.append(uri)

        return urls
