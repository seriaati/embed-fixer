from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "guild_fixes" DROP CONSTRAINT "guild_fixes_guild_id_fkey";
        ALTER TABLE "guild_fixes"
            ADD CONSTRAINT "guild_fixes_guild_id_fkey"
            FOREIGN KEY (guild_id) REFERENCES "guild_settings_v2" (id);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "guild_fixes" DROP CONSTRAINT "guild_fixes_guild_id_fkey";
        ALTER TABLE "guild_fixes"
            ADD CONSTRAINT "guild_fixes_guild_id_fkey"
            FOREIGN KEY (guild_id) REFERENCES "guild_settings" (id);"""
