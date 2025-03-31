# pyright: reportAssignmentType=false

from __future__ import annotations

from typing import TYPE_CHECKING

from attr import dataclass
from pydantic import BaseModel, field_validator
from tortoise import fields
from tortoise.models import Model

from embed_fixer.utils.misc import remove_html_tags

if TYPE_CHECKING:
    import discord


class GuildSettings(Model):
    id = fields.BigIntField(pk=True, generated=False)
    disable_webhook_reply = fields.BooleanField(default=False)
    disabled_fixes: fields.Field[list[str]] = fields.JSONField(default=[])
    disable_fix_channels: fields.Field[list[int]] = fields.JSONField(default=[])
    extract_media_channels: fields.Field[list[int]] = fields.JSONField(default=[])
    disable_image_spoilers: fields.Field[list[int]] = fields.JSONField(default=[])
    show_post_content_channels: fields.Field[list[int]] = fields.JSONField(default=[])
    disable_delete_reaction = fields.BooleanField(default=False)
    lang: fields.Field[str | None] = fields.CharField(max_length=5, null=True)
    use_vxreddit = fields.BooleanField(default=False)
    delete_msg_emoji = fields.CharField(max_length=100, default="❌")

    class Meta:
        table = "guild_settings"


class PixivArtworkInfo(BaseModel):
    tags: list[str]
    image_urls: list[str]
    description: str
    author_name: str
    author_id: str

    @field_validator("description", mode="after")
    @classmethod
    def __format_description(cls, v: str) -> str:
        return remove_html_tags(v.replace("  ", "\n"))

    @property
    def author_md(self) -> str:
        return f"[{self.author_name}](<https://www.pixiv.net/users/{self.author_id}>)"


@dataclass(kw_only=True)
class TwitterPostInfo:
    media_urls: list[str]
    content: str
    author_name: str
    author_handle: str

    @property
    def author_md(self) -> str:
        return f"[{self.author_name} (@{self.author_handle})](<https://twitter.com/{self.author_handle}>)"


@dataclass(kw_only=True)
class BlueskyPostInfo:
    media_urls: list[str]
    content: str
    author_name: str
    author_handle: str

    @property
    def author_md(self) -> str:
        return f"[{self.author_name} (@{self.author_handle})](<https://bsky.app/profile/{self.author_handle}>)"


@dataclass(kw_only=True)
class Media:
    url: str
    file: discord.File | None = None


@dataclass(kw_only=True)
class PostExtractionResult:
    medias: list[Media]
    content: str
    author_md: str


@dataclass(kw_only=True)
class FindFixResult:
    fix_found: bool
    medias: list[Media]
    sauces: list[str]
    content: str
    author_md: str
