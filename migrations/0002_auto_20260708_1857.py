from tortoise import migrations
from tortoise.migrations import operations as ops
from tortoise import fields
from tortoise.indexes import Index


class Migration(migrations.Migration):
    dependencies = [("embed_fixer", "0001_initial")]

    initial = False

    operations = [
        ops.CreateModel(
            name="FixedMessage",
            fields=[
                ("id", fields.BigIntField(primary_key=True, unique=True, db_index=True, generated=False)),
                ("guild_id", fields.BigIntField()),
                ("channel_id", fields.BigIntField()),
                ("author_id", fields.BigIntField()),
                ("send_type", fields.CharField(max_length=16)),
                (
                    "created_at",
                    fields.DatetimeField(db_index=True, auto_now=False, auto_now_add=True),
                ),
            ],
            options={
                "table": "fixed_messages",
                "app": "embed_fixer",
                "pk_attr": "id",
                "table_description": "A fixed message sent by the bot, used to recognize it and its original author later.",
            },
            bases=["Model"],
        )
    ]
