from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "guild_settings" ALTER COLUMN "funnel_target_channel" TYPE BIGINT USING "funnel_target_channel"::BIGINT;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "guild_settings" ALTER COLUMN "funnel_target_channel" TYPE INT USING "funnel_target_channel"::INT;"""
