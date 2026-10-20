from tortoise import migrations
from tortoise.migrations import operations as ops
from tortoise import fields


class Migration(migrations.Migration):
    dependencies = [("embed_fixer", "0002_auto_20260708_1857")]

    initial = False

    operations = [
        ops.CreateModel(
            name="SponsoredGuild",
            fields=[
                (
                    "id",
                    fields.BigIntField(
                        primary_key=True, unique=True, db_index=True, generated=False
                    ),
                ),
                ("sponsor_id", fields.BigIntField(null=True)),
            ],
            options={
                "table": "sponsored_guilds",
                "app": "embed_fixer",
                "pk_attr": "id",
                "table_description": "A guild with a sponsor-only feature enabled, and the administrator sponsor unlocking it.",
            },
            bases=["Model"],
        )
    ]
