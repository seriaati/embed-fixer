# pyright: reportAssignmentType=false

from __future__ import annotations

from tortoise import fields
from tortoise.models import Model


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
