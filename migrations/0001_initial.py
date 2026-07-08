# pyright: reportAssignmentType=false, reportArgumentType=false

from tortoise import migrations
from tortoise.migrations import operations as ops
import functools
from embed_fixer.fixes import DomainId
from json import dumps, loads
from tortoise.fields.base import OnDelete
from tortoise import fields


class Migration(migrations.Migration):
    initial = True

    operations = [
        ops.CreateModel(
            name="GuildSettingsOld",
            fields=[
                ("id", fields.BigIntField(primary_key=True, unique=True, db_index=True, generated=False)),
                ("disable_webhook_reply", fields.BooleanField(default=False)),
                (
                    "disabled_fixes",
                    fields.JSONField(
                        default=[],
                        encoder=functools.partial(dumps, separators=(",", ":")),
                        decoder=loads,
                    ),
                ),
                (
                    "disabled_domains",
                    fields.JSONField(
                        default=[],
                        encoder=functools.partial(dumps, separators=(",", ":")),
                        decoder=loads,
                    ),
                ),
                (
                    "disable_fix_channels",
                    fields.JSONField(
                        default=[],
                        encoder=functools.partial(dumps, separators=(",", ":")),
                        decoder=loads,
                    ),
                ),
                (
                    "enable_fix_channels",
                    fields.JSONField(
                        default=[],
                        encoder=functools.partial(dumps, separators=(",", ":")),
                        decoder=loads,
                    ),
                ),
                (
                    "extract_media_channels",
                    fields.JSONField(
                        default=[],
                        encoder=functools.partial(dumps, separators=(",", ":")),
                        decoder=loads,
                    ),
                ),
                (
                    "disable_image_spoilers",
                    fields.JSONField(
                        default=[],
                        encoder=functools.partial(dumps, separators=(",", ":")),
                        decoder=loads,
                    ),
                ),
                (
                    "show_post_content_channels",
                    fields.JSONField(
                        default=[],
                        encoder=functools.partial(dumps, separators=(",", ":")),
                        decoder=loads,
                    ),
                ),
                ("disable_delete_reaction", fields.BooleanField(default=False)),
                ("lang", fields.CharField(null=True, max_length=5)),
                ("use_vxreddit", fields.BooleanField(default=False)),
                ("delete_msg_emoji", fields.CharField(default="❌", max_length=100)),
                ("bot_visibility", fields.BooleanField(default=False)),
                ("funnel_target_channel", fields.BigIntField(null=True)),
                (
                    "whitelist_role_ids",
                    fields.JSONField(
                        default=[],
                        encoder=functools.partial(dumps, separators=(",", ":")),
                        decoder=loads,
                    ),
                ),
                ("translate_target_lang", fields.CharField(null=True, max_length=5)),
                ("show_original_link_btn", fields.BooleanField(default=False)),
            ],
            options={"table": "guild_settings", "app": "embed_fixer", "pk_attr": "id"},
            bases=["Model"],
        ),
        ops.CreateModel(
            name="GuildSettingsTable",
            fields=[
                ("id", fields.BigIntField(primary_key=True, unique=True, db_index=True, generated=False)),
                (
                    "data",
                    fields.JSONField(
                        default=dict,
                        encoder=functools.partial(dumps, separators=(",", ":")),
                        decoder=loads,
                    ),
                ),
            ],
            options={"table": "guild_settings_v2", "app": "embed_fixer", "pk_attr": "id"},
            bases=["SettingsTable"],
        ),
        ops.CreateModel(
            name="GuildFixMethod",
            fields=[
                (
                    "id",
                    fields.IntField(generated=True, primary_key=True, unique=True, db_index=True),
                ),
                (
                    "guild",
                    fields.ForeignKeyField(
                        "embed_fixer.GuildSettingsTable",
                        source_field="guild_id",
                        db_constraint=True,
                        to_field="id",
                        related_name="embed_fixes",
                        on_delete=OnDelete.CASCADE,
                    ),
                ),
                (
                    "domain_id",
                    fields.IntEnumField(
                        description="TWITTER: 1\nPIXIV: 2\nTIKTOK: 3\nREDDIT: 4\nINSTAGRAM: 5\nFURAFFINITY: 6\nTWITCH_CLIPS: 7\nIWARA: 8\nBLUESKY: 9\nKEMONO: 10\nFACEBOOK: 11\nBILIBILI: 12\nTUMBLR: 13\nTHREADS: 14\nPTT: 15\nDEVIANTART: 16\nBILIBILI_OPUS: 17",
                        enum_type=DomainId,
                        generated=False,
                    ),
                ),
                ("fix_id", fields.IntField()),
            ],
            options={
                "table": "guild_fixes",
                "app": "embed_fixer",
                "unique_together": (("guild_id", "domain_id", "fix_id"),),
                "pk_attr": "id",
            },
            bases=["Model"],
        ),
        ops.CreateModel(
            name="IgnoreMe",
            fields=[("id", fields.BigIntField(primary_key=True, unique=True, db_index=True, generated=False))],
            options={"table": "ignore_me", "app": "embed_fixer", "pk_attr": "id"},
            bases=["Model"],
        ),
        ops.CreateModel(
            name="UserSettingsTable",
            fields=[
                ("id", fields.BigIntField(primary_key=True, unique=True, db_index=True, generated=False)),
                (
                    "data",
                    fields.JSONField(
                        default=dict,
                        encoder=functools.partial(dumps, separators=(",", ":")),
                        decoder=loads,
                    ),
                ),
            ],
            options={"table": "user_settings", "app": "embed_fixer", "pk_attr": "id"},
            bases=["SettingsTable"],
        ),
    ]
