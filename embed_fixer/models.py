# pyright: reportAssignmentType=false

from __future__ import annotations

from tortoise import fields
from tortoise.models import Model

from embed_fixer.fixes import DomainId


class GuildSettings(Model):
    id = fields.BigIntField(pk=True, generated=False)
    disable_webhook_reply = fields.BooleanField(default=False)
    disabled_fixes: fields.Field[list[str]] = fields.JSONField(default=[])
    disabled_domains: fields.Field[list[int]] = fields.JSONField(default=[])
    disable_fix_channels: fields.Field[list[int]] = fields.JSONField(default=[])
    enable_fix_channels: fields.Field[list[int]] = fields.JSONField(default=[])
    extract_media_channels: fields.Field[list[int]] = fields.JSONField(default=[])
    disable_image_spoilers: fields.Field[list[int]] = fields.JSONField(default=[])
    show_post_content_channels: fields.Field[list[int]] = fields.JSONField(default=[])
    disable_delete_reaction = fields.BooleanField(default=False)
    lang: fields.Field[str | None] = fields.CharField(max_length=5, null=True)
    use_vxreddit = fields.BooleanField(default=False)
    delete_msg_emoji = fields.CharField(max_length=100, default="❌")
    bot_visibility = fields.BooleanField(default=False)
    funnel_target_channel: fields.Field[int | None] = fields.BigIntField(null=True)
    whitelist_role_ids: fields.Field[list[int]] = fields.JSONField(default=[])
    translate_target_lang: fields.Field[str | None] = fields.CharField(max_length=5, null=True)

    class Meta:
        table = "guild_settings"

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({', '.join(f'{field}={getattr(self, field)!r}' for field in self._meta.db_fields if hasattr(self, field))})"


class GuildFixMethod(Model):
    guild: fields.ForeignKeyRelation[GuildSettings] = fields.ForeignKeyField(
        "embed_fixer.GuildSettings", related_name="embed_fixes"
    )
    domain_id: fields.Field[DomainId] = fields.IntEnumField(DomainId)
    fix_id = fields.IntField()
    guild_id: fields.Field[int]

    class Meta:
        table = "guild_fixes"
        unique_together = ("guild_id", "domain_id", "fix_id")
