from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "guild_settings" ADD "use_vxreddit" BOOL NOT NULL DEFAULT False;
        ALTER TABLE "guild_settings" ALTER COLUMN "lang" TYPE VARCHAR(5) USING "lang"::VARCHAR(5);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "guild_settings" DROP COLUMN "use_vxreddit";
        ALTER TABLE "guild_settings" ALTER COLUMN "lang" TYPE VARCHAR(5) USING "lang"::VARCHAR(5);"""
