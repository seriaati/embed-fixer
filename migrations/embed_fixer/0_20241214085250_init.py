from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "guild_settings" (
    "id" BIGINT NOT NULL  PRIMARY KEY,
    "disable_webhook_reply" BOOL NOT NULL  DEFAULT False,
    "disabled_fixes" JSONB NOT NULL,
    "disable_fix_channels" JSONB NOT NULL,
    "extract_media_channels" JSONB NOT NULL,
    "disable_image_spoilers" JSONB NOT NULL,
    "lang" VARCHAR(5)
);
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
