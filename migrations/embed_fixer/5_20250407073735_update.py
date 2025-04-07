from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "guild_fixes" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "domain_id" SMALLINT NOT NULL,
    "fix_id" INT NOT NULL,
    "guild_id" BIGINT NOT NULL REFERENCES "guild_settings" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_guild_fixes_guild_i_44e5aa" UNIQUE ("guild_id", "domain_id", "fix_id")
);
COMMENT ON COLUMN "guild_fixes"."domain_id" IS 'TWITTER: 1\nPIXIV: 2\nTIKTOK: 3\nREDDIT: 4\nINSTAGRAM: 5\nFURAFFINITY: 6\nTWITCH_CLIPS: 7\nIWARA: 8\nBLUESKY: 9\nKEMONO: 10\nFACEBOOK: 11\nBILIBILI: 12\nTUMBLR: 13\nTHREADS: 14';
        ALTER TABLE "guild_settings" ADD "disabled_domains" JSONB NOT NULL DEFAULT '[]';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "guild_settings" DROP COLUMN "disabled_domains";
        DROP TABLE IF EXISTS "guild_fixes";"""
