# pyright: reportAssignmentType=false

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

import pydantic
from tortoise import fields
from tortoise.exceptions import IntegrityError
from tortoise.models import Model

from embed_fixer.fixes import DomainId

if TYPE_CHECKING:
    from collections.abc import Iterable


class IgnoreMe(Model):
    id = fields.BigIntField(pk=True, generated=False)

    class Meta:
        table = "ignore_me"

    @classmethod
    async def add(cls, id: int) -> None:  # noqa: A002
        with contextlib.suppress(IntegrityError):
            await cls.create(id=id)

    @classmethod
    async def remove(cls, id: int) -> None:  # noqa: A002
        await cls.filter(id=id).delete()

    @classmethod
    async def contains(cls, id: int) -> bool:  # noqa: A002
        return await cls.filter(id=id).exists()

    @classmethod
    async def toggle(cls, id: int) -> bool:  # noqa: A002
        if await cls.contains(id):
            await cls.remove(id)
            return False
        await cls.add(id)
        return True


class GuildSettingsTable(Model):
    id = fields.BigIntField(pk=True, generated=False)
    data = fields.JSONField(default={})

    class Meta:
        table = "guild_settings_v2"


class GuildSettings(pydantic.BaseModel):
    id: int
    disable_webhook_reply: bool = False
    disabled_fixes: list[str] = pydantic.Field(default_factory=list)
    disabled_domains: list[int] = pydantic.Field(default_factory=list)
    disable_fix_channels: list[int] = pydantic.Field(default_factory=list)
    enable_fix_channels: list[int] = pydantic.Field(default_factory=list)
    extract_media_channels: list[int] = pydantic.Field(default_factory=list)
    disable_image_spoilers: list[int] = pydantic.Field(default_factory=list)
    show_post_content_channels: list[int] = pydantic.Field(default_factory=list)
    disable_delete_reaction: bool = False
    lang: str | None = None
    use_vxreddit: bool = False
    delete_msg_emoji: str = "❌"
    bot_visibility: bool = False
    funnel_target_channel: int | None = None
    whitelist_role_ids: list[int] = pydantic.Field(default_factory=list)
    translate_target_lang: str | None = None
    show_original_link_btn: bool = True

    @classmethod
    async def get_or_create(cls, id: int) -> tuple[GuildSettings, bool]:  # noqa: A002
        obj, created = await GuildSettingsTable.get_or_create(id=id)
        if created or not obj.data:
            settings = cls(id=id)
            await settings.save()
            return settings, created
        return cls(id=id, **obj.data), created

    @classmethod
    async def get_or_none(cls, id: int) -> GuildSettings | None:  # noqa: A002
        obj = await GuildSettingsTable.get_or_none(id=id)
        if obj is None or not obj.data:
            return None
        return cls(id=id, **obj.data)

    @classmethod
    async def create(cls, id: int) -> GuildSettings:  # noqa: A002
        settings = cls(id=id)
        await settings.save()
        return settings

    @classmethod
    async def delete(cls, id: int) -> None:  # noqa: A002
        await GuildSettingsTable.filter(id=id).delete()

    async def save(self, *, update_fields: Iterable[str] | None = None) -> None:  # noqa: ARG002
        obj, _ = await GuildSettingsTable.get_or_create(id=self.id)
        obj.data = self.model_dump(exclude={"id"})
        await obj.save()


# Deprecated, only for migration, new fields should be added to GuildSettings
class GuildSettingsOld(Model):
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
    show_original_link_btn = fields.BooleanField(default=False)

    class Meta:
        table = "guild_settings"

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({', '.join(f'{field}={getattr(self, field)!r}' for field in self._meta.db_fields if hasattr(self, field))})"


class GuildFixMethod(Model):
    guild: fields.ForeignKeyRelation[GuildSettingsTable] = fields.ForeignKeyField(
        "embed_fixer.GuildSettingsTable", related_name="embed_fixes"
    )
    domain_id: fields.Field[DomainId] = fields.IntEnumField(DomainId)
    fix_id = fields.IntField()
    guild_id: fields.Field[int]

    class Meta:
        table = "guild_fixes"
        unique_together = ("guild_id", "domain_id", "fix_id")
