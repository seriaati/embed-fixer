from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "guild_fixes" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "domain_id" SMALLINT NOT NULL,
    "fix_id" INT NOT NULL,
    "guild_id" BIGINT NOT NULL REFERENCES "guild_settings" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_guild_fixes_guild_i_44e5aa" UNIQUE ("guild_id", "domain_id", "fix_id")
);
COMMENT ON COLUMN "guild_fixes"."domain_id" IS 'TWITTER: 1
PIXIV: 2
TIKTOK: 3
REDDIT: 4
INSTAGRAM: 5
FURAFFINITY: 6
TWITCH_CLIPS: 7
IWARA: 8
BLUESKY: 9
KEMONO: 10
FACEBOOK: 11
BILIBILI: 12
TUMBLR: 13
THREADS: 14';
        ALTER TABLE "guild_settings" ADD "disabled_domains" JSONB NOT NULL DEFAULT '[]';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "guild_settings" DROP COLUMN "disabled_domains";
        DROP TABLE IF EXISTS "guild_fixes";"""


MODELS_STATE = (
    "eJzlWVtv2koQ/ivITz1Sz1FCSKC8GQKJD7cKnLZHAVmLvTF7Yu9Se90QRfz3zvqCjbk4OL"
    "hqwwNCnll/M/5mdmY9fpGwPcWG9kAW2PlHxg7RZ1K99CKh+Rz+k1rpY0miyMYpcXQTaDma"
    "Wr4arUSEGniBXRDeT+DSRhSZ2IBL6lkWCNDU5Q7SOUgekOViEM0fARhbhu9GZJAYAs2j5L"
    "snrrnjiaUGfkCexWO4wJwRrxDy0KsI35hqOrM8m8a4BtPBDULNGMnEFDuIJ7F8rzT+PPc9"
    "Uihv+26CRmdUPAah3PW9NsWKv8vnlWqldnFVqcES34WVpLr0vXd1h8w5YTS2O3/mM0ZXVg"
    "BSCnyOrQc2fB/6qrRcbn+Ah5DGmPuynZKwMktJDMRRQhTz/wM7rvAzGYQVobujEC3JCkMC"
    "PiMW0e3rwWjOkLMzGjZaaBamJheZXb68fC33ALKH+y/ysHkrDz8A4F9iGYM0DrK/H6rKgU"
    "4EKCZS7KuCSAyhCybw/OzsuAQC4E4Cfd06geAcx8GuKILEBHwuIv8dDfq7iHwtb3cUtPcG"
    "0fnHkkVcPtnDorAn1LbrfreS5H3oyd/SvDa7g4YQzZnLTcdH8QEawPFkl3MByxpnJuYzaA"
    "NhqZgi/fEJOdAF0oVmpUnVF/H4ycZx4xHLGGHOgWL3wKazfm+y95hCo7kJ1bvoQduzrUHM"
    "7D70qVy+uKiWzy6uapeVavWydrZqSJuqI3WmhnIjmtNa+v26bmUQVxCuPeHpjLFHzcFz6z"
    "mjYkSSw0vGTmv5QsqYhRF9aw2ZAsy++AwG3bWy0VBS0erf9RotqM5+DYFFhK8FcYPsYGe6"
    "GSxL9xPpLSQnrJxWed7KuMFs8L54zhN2Tp51kYCaPkOUYqto5jdsnS77eOH3aM3GBkGF87"
    "/b2ulGIMpJYsPxSXPnjFjw1lb0Dti0droRcGfsSROLtPAtpfB9sN/i6UYiyk4DW5hjOPFB"
    "scgej7z9iLnF3mkcMi0ED7if3de88kfvbEluI+iC5yZHHjvtHjptjJw8F2s/Fg42DJI1Ns"
    "mfoWkjp5GW4X60XVPDNvufZNXhsVeuVvScHXGLrXc46zvOHOply9Qoq0seNDPMld6hq+3O"
    "EFsoKuA5k3xjGtYmix4wwwwpypwINyx8y4OHczFkjuncmj+p8dwqHO9iNvfnfx+KifTj8+"
    "s3CjxSUN/8AiWPmvJ1S3jhoKdVtMPcCUKyTnabOZiYtIOffc4VoBtRHR9zeyWHzTt319um"
    "lv6URSNHpX+tgyQN5KpgkNQt6tlZJIcJflGuXq1yW1xsSWtJ/aqoamsIzWZMPyvflC+wDc"
    "ZUVTrqoAN3jemwdX2tqPVSZUyV/kiVb4ZyD45TY9q+G8rtttJX1P/qpSu4B5Cat1qzq3we"
    "1UtVWP5VHsr1Um1MG9271qgDyz6NaafVG/QHorkBhNxswXEADJ2D+YbSVcQProQLcAjoCr"
    "/AB/V22JKvAfW8Ih26CUc9udvdPDqI0U5xoY7R88b5tyleqdpUIGlJ/FP5HHPIces+xVCi"
    "moT5Nsn5ZXD5Ewg1EyM="
)
