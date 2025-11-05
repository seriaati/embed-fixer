from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "guild_settings" ADD "show_original_link_btn" BOOL NOT NULL DEFAULT False;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "guild_settings" DROP COLUMN "show_original_link_btn";"""


MODELS_STATE = (
    "eJzlWm1v4jgQ/ison/akvVNLaenyLVBoc7xVkO7uqVSWSdzga2KzidNSVf3vOw4JCYFAoa"
    "S6az5UVcbOPJNnxjNjmxeFOGNions6I+5fKnGpMVFqpRcFT6fwPzmqfC0pDDskJY5eglGB"
    "x3YwjBciykwyIx4Ib+/g0cEMW8SER+bbNgjw2BMuNgRI7rHtERBNH0Axsc3AjAiQmlKbz+"
    "gvXz4L15dTTXKPfVvE6uZwZjxDykOrIv3mGBnc9h0W6zW5AWZQZsWaLMKIi0VSV2AVEs/T"
    "wCKNiVZgJowYnMnPoEx4gdWWnPFn+bhSrZyfnFXOYUpgwkJSfQ2s9wyXTgXlLMadPosJZw"
    "sUUKnMbY7R5xiBDT1deX1d/wH3IY0x92UnJeFlnpKYWOCEKOb/kbietDPphAWh2V6Ipmxz"
    "Q0L9Fl9Ery87ozHBbqY3HDxDNmGWkJFdPj19K/egZAP339VB40odfAGFf8hpHMJ4Hv29cK"
    "g8H5MOiomU6yonEkPVORN4fHR0WAJBYSaBwdgygWCcIPNVkQeJCfV7Efn3sN/LIvKtvN0w"
    "GL01qSG+lmzqibsNLEo8Oex43i87Sd6XrvozzWuj069L0ZR7wnIDLYGCOnB8l2XcnGUkuE"
    "XEBMpAmCrG2Hh4wi5UgXSiWYyk8ov8/GThuPSpbQ6JEECxt2PRWX43WXssOYK8xNCnqEHr"
    "o61Ore116Fu5fHJSLR+dnJ2fVqrV0/OjRUFaHTpQZaprl7I4LYXfx1Urk3qScPRExhPOH5"
    "BLpvbzlowRSXZPGZlo+7mUc5tg9t4cMgY1m/zT73eW0kZdS3mrd9OtNyE7BzkEJlGx5MQV"
    "sucr09vCsnJ7p7yH5ARKsdLzWsZN7oD1+XOewCk86zIAkTHBjBE7b+ZXsIrLPmEfRn4GVI"
    "G5nwX9EXKISXH+9GeiFdcDUT6gDrSuyJtyasOOOe/ss4pWXA94E/6E5CQU7hBzXwebEYvr"
    "iSg6TWITQaDbhmSx/Wjq/e39GrxiNPg2hg/czO5bjlui/XKS20h1zmdWBz7yyz7wWznu8z"
    "2CHmcuMU267chq/whNgxQjLMP16HgWIg7/l27LwyO/XK0Ye1bENVif/Jx1zAV6pB4dU3BB"
    "focnqzDFiN57X5ZyJLBrkUVlzynLZmIV58wxJv5pAj6RjQtyuexxzdwauPVIxW3cwGbm2f"
    "CdUSTm2FhkYn3aTiPYLnCXWpRhG9mUPaCxyK8rzob7vPn7MFdkL2sutLbloJ2uM/fiPzS1"
    "1R4QWDbh/mZPL6xc1LXorAvMcFOJwijSGy7f153vDWOVe1wcLtmTujlcuONTXBv+/3+6Eh"
    "MZ+OfjFwp80rz9DyqBOmyoF01phYufFt4OY2fukmWyW9wl1GJt8hxwrgHdmBnkkMsreQ+e"
    "ubred6EaXAAhelD6lzZYSYC9MhgEdZP5zjaSwwA/KVfPFrEtH9aEtaL/0HS9OYC92Ihdaz"
    "+177AMRkzX2nq/DW+N2KB5caHptVJlxLTeUFcvB2oXeoARa90M1FZL62n6P7XSGbwDmhpX"
    "qNHRroe1UhWm/1AHaq10PmL1zk1z2IZp30as3ez2e3259wMVaqMJ9QqAjgG+rnU0+QdP0g"
    "SoUh1pF9igXw2a6gVoPQYrrnWw5vhU2XU1Drtqp7Nmk0JnOfo81r6vw/8zWSyVpHIkLam/"
    "KNu3Xfqu2xRDibQSxtvdnr9eev0NyDzbbQ=="
)
