# pyright: reportAssignmentType=false

from __future__ import annotations

from attr import dataclass
from tortoise import fields
from tortoise.models import Model


class GuildSettings(Model):
    id = fields.BigIntField(pk=True, generated=False)
    disable_webhook_reply = fields.BooleanField(default=False)
    disabled_fixes: fields.Field[list[str]] = fields.JSONField(default=[])
    disable_fix_channels: fields.Field[list[int]] = fields.JSONField(default=[])
    extract_media_channels: fields.Field[list[int]] = fields.JSONField(default=[])
    disable_image_spoilers: fields.Field[list[int]] = fields.JSONField(default=[])
    lang: fields.Field[str | None] = fields.CharField(max_length=5, null=True)

    class Meta:
        table = "guild_settings"


@dataclass
class PixivArtworkInfo:
    tags: list[str]
    image_urls: list[str]
