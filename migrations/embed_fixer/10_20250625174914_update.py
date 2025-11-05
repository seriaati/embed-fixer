from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "guild_settings" ADD "whitelist_role_ids" JSONB DEFAULT '[]' NOT NULL;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "guild_settings" DROP COLUMN "whitelist_role_ids";"""


MODELS_STATE = (
    "eJzlWm1zokgQ/isWn/aq9q4SX2LWb2g04XxLKdndq2hRI4w4F5hxYUhMpfLftwdBEEWjkd"
    "Rd+LC1RffwdPN0T3c7kxcJ2xNsaFOywM5fMnaIPpNqhRcJzefwf1wrfS1IFNk4IQ5fAi1H"
    "E8tXo5WIUAMvsAvC+zE82ogiExvwSD3LAgGauNxBOgfJFFkuBtH8AYCxZfhuhAaJIdA8Sn"
    "554pk7nlhq4CnyLB7BLc0Z0QohD7wK8Y2JpjPLs2mEazAd3CDUjJBMTLGDeBzL90rjz3Pf"
    "I4Xylu8maHRGxWcQyl3fa1Os+LN4Xq6WL0sX5UtY4ruwklRffe9d3SFzThiN7M6f+YzRlR"
    "WAlJY+R9aXNnwfeqr0+rr9A6YBjRH3RTshYUWWkBiIo5go4v8RO67wMx6EFaHpUQiX7AtD"
    "DH5PLMLX14PRmCEnNRo2WmgWpiYXmV2sVN7KPYDs4P67PGjcyIMvAPiHWMYgjZfZ3wtUxa"
    "VOBCgiUuyrjEgMoDMm8Pzs7LQEAmAqgb5unUBwjuPlrsiCxBj8UUT+Pez30oh8K293FLT3"
    "BtH514JFXD7ewaKwJ9S26/6y4uR96co/k7w2Ov26EM2Zy03HR/EB6sDxOM25JcsaZybmM2"
    "gDQamYIP3hCTnQBZKFZqVJ1Bfx+fHGce0RyxhizoFi98Cms/5uvPeYQqO5MdWn6EHbs61O"
    "zP196FuxWCpVi2eli8tKuVqtXJ6tGtKm6kSdqa5ci+a0ln4f160M4grCtSc8mTH2oDl4bj"
    "3vqRih5PCSkWrtuJAyZmFE31tDJgCzKz79fmetbNSVRLR6d916E6qzX0NgEeFrQdwge7kz"
    "3T0sS/dj6T0kx6zkqzxvZdxgNnifPecxO7lnXSSgps8QpdjKmvkNW/llH9MPIz/FVI65X/"
    "jzkWZjg6Ds6U+1lt8IhPWA2DC6au6cEQt+MWddfTat5TcC7ow9aWKRFvxCzHwf7LaY30iE"
    "2WlgC3MM0zYUi/1HU+8f77fYy8eAbyH4wN3svuW4Jfy9HOc2hM74zOrER37pB34bx32ei7"
    "XHhYMNg+w7sjo+Q5NG8pGWwX60XVPDNvuX7KvDI69YLetHdsQttj75OeuEce2RuGRCIATZ"
    "HZ5smslH9k490co1jhwTrzp7RlU21VZ+zhwj4p9mEBMxuGgOEzOukdkAt91Svga309wqvG"
    "y5A9gXtoNugI7aB4GrrfYAWygcCY8MzsbdRossusAMM6QwrULcYJO/HnzVEkEecdey5k/i"
    "smUVjk9x0/L/v+2PiPTj8/EbBT5pOTH5I488bMhXTeGFg55W0Q5yZxmSdbJbzMHEpG387H"
    "OuAN2I6viU2yt+dZi6u953B+WfmWvkpPSvzaRxA0dVMEjqJvXsfSQHCV4qVi9WuS0etqS1"
    "pP5QVLU5gPF1RG+Vn8p32AYjqipttd+Gt0Z00Ly6UtRaoTyiSm+oytcDuQs/0Ea0dTeQWy"
    "2lp6j/1AoX8A4gNW60Rke5HdYKVVj+Qx7ItcLliNY7d81hG5Z9G9F2s9vv9cW4DBByowkj"
    "Ghg6B/N1paOIf/AkXIDBrCP8Ah/Um0FTvgLUc/DiVgVvzivSobtx2JU7nS1zHVlkGPMI/d"
    "iA/2eqWKJIZUhaHD8vE+8hc9d9gqFYWQnybXzkH3y8/gaxZfEz"
)
