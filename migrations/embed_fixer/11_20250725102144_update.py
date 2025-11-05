from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "guild_settings" ADD "translate_target_lang" VARCHAR(5);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "guild_settings" DROP COLUMN "translate_target_lang";"""


MODELS_STATE = (
    "eJzlWm1v4jgQ/ison/akvVNLobB8CxTaHG8VpLt7KlVkEhN8TWw2cQpV1f++45CQEAgUSq"
    "q75kNVZezMM3lmPDO2eZGwPcaGNiEL7PwlY4foU6lWeJHQbAb/46PS14JEkY0T4vAlGOVo"
    "bPnDaCUi1MAL7ILw/gEebUSRiQ14pJ5lgQCNXe4gnYNkgiwXg2j2CIqxZfhmhIDEENo8Sn"
    "554pk7nphq4AnyLB6pW8IZ0QwhD6wK9RtjTWeWZ9NIr8F0MINQM9JkYoodxOO6fKs0/jzz"
    "LVIob/lmwojOqPgMQrnrW22KGX8Wz0uVUvXislSFKb4JK0nl1bfe1R0y44TRCHf2zKeMrl"
    "BApbS0OUJfYvg29FTp9XX7B0wCGiPui3ZCwoosITEQRzFRxP8TdlxhZ9wJK0LTvRBO2eeG"
    "mPo9vghfX3dGY4qcVG/YaKFZmJpcRHaxXH4r96BkB/ff5UHjRh58AYV/iGkMwngZ/b1gqL"
    "gcEw6KiBTrKiMSA9UZE3h+dnZaAkFhKoH+2DqBYBzHy1WRBYkx9UcR+few30sj8q283VEY"
    "vTeIzr8WLOLyhx0sCjwxbLvuLytO3peu/DPJa6PTrwvRjLncdHwtvoI6cPyQZtySZY0zE/"
    "MplIEgVYyR/jhHDlSBZKJZjSTyi/j8eOG49ohlDDHnQLF7YNFZfzdee0wxormxoU9Rg7ZH"
    "W52Y++vQt2Lx4qJSPLu4rJZLlUq5erYqSJtDJ6pMdeVaFKe18Pu4amUQVxCuzfF4ytij5u"
    "CZ9bwnY4SSw1NGKtpxLmXMwoi+N4eMQc0u//T7nbW0UVcS3urddetNyM5+DoFJhK85cYPs"
    "5cp097As3T9I7yE5hpKv9LyVcYPZYH32nMdwcs+6CEBNnyJKsZU18xtY+WUf0w8jPwUqx9"
    "wv/P5Is7FBUPb0p6Ll1wNhPiA2tK6aO2PEgh1z1tlnEy2/HnCnbK6JSVqwQ8x8HexGzK8n"
    "wug0sIU5hm4bksX+o6n3t/db8PLR4FsIPnA3u285bgn3y3FuQ9UZn1md+Mgv/cBv47jPc7"
    "H2tHCwYZB9R1bHR2gSJB9hGaxH2zU1bLN/yb48PPKKlZJ+ZEXcgvXJz1nHjGtPxCVjAi7I"
    "7vBkEyYf0TvxRCnXOHJMvKrsGWXZVKz8nDlGxM+n4BPRuGgOEz2ukVkDtx0pv40b2ExdC7"
    "4zjMQMG4tUrE/VaZzmzuZlyw3LvkVx0P3aUVkmMLXVHmDwY9BwHxn6GzdHLbLoAjPMkMLA"
    "CfUG8fR68EVWpPKIm6w1exJXWSt3fIp7rP//bykiIn3/fPxCgU9a9qN+apKHDfmqKaxw0H"
    "zl7SB2li5ZJ7vFHExM2sbPPucK0I2ojk+5vOIXs6mr6303fP6NhEZOSv9axx8HOCqDQVA3"
    "qWfvIzkI8Iti5XIV2+JhS1hL6g9FVZsD2ByM6K3yU/kOy2BEVaWt9tvw1ogOmldXilorlE"
    "ZU6Q1V+Xogd6EojWjrbiC3WkpPUf+pFS7hHdDUuNEaHeV2WCtUYPoPeSDXCtURrXfumsM2"
    "TPs2ou1mt9/ri80IqJAbTWiAAegc4OtKRxF/8CRMgLa3I+wCG9SbQVO+Aq3nYMWtCtacl6"
    "VDV+OwK3c6W7pmssjQ55H2Yx3+n8liiSSVIWlx/XnZTxzSd90nGIqllSDeHo78Oc3rb4IQ"
    "Y+o="
)
