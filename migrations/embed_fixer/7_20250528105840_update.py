from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "guild_settings" ADD "bot_visibility" BOOL NOT NULL DEFAULT False;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "guild_settings" DROP COLUMN "bot_visibility";"""


MODELS_STATE = (
    "eJzlWW1zokgQ/isWn/aq9q4SNNH1GxpNON+2lOzuVbSoESY4F5hxYUxMpfzv24MgiKLRSG"
    "o3fLAsuoenm6d7uofmRcLOGJv6PZlj9x8Fu8SYSNXCi4SmU/iPa6XPBYkiByfE4U2g5Whs"
    "+2q0EhFq4jn2QHg3gksHUWRhEy7pzLZBgMYed5HBQXKPbA+DaPoAwNg2fTdCg8QUaDNKfs"
    "7ENXdnYqmJ79HM5hHc0pwZrRDywKsQ3xzrBrNnDo1wTWaAG4RaEZKFKXYRj2P5Xun8eep7"
    "pFLe9N0EjcGoeAxCued7bYkVf8vnpXKpUrwsVWCJ78JKUl743nuGS6acMBrZnT7zCaMrKw"
    "ApLX2OrC9t+D50NWmx2P4A9wGNEfeyk5AwmSUkJuIoJor4f8SuJ/yMB2FFaHoUwiX7whCD"
    "3xOL8Pb1YNQnyE2NhoPmuo2pxUVmyxcXr+UeQHZw/03p12+U/icA/EssY5DGy+zvBip5qR"
    "MBiogU+yojEgPojAk8Pzs7LYEAmEqgr1snEJzjeLkrsiAxBn8Ukf8Oet00Il/L2y0F7Z1J"
    "DP65YBOPj3awKOwJteN5P+04eZ86yo8kr/V2ryZEU+Zxy/VRfIAacDxKc27Jss6ZhfkE2k"
    "BQKsbIeHhCLnSBZKFZaRL1RTx+vHFcz4htDjDnQLF3YNNZvzfeeyyh0b2Y6kP0oO3ZViPW"
    "/j70RZaLxbJ8VrysXJTK5YvK2aohbapO1Jlq6rVoTmvp937dyiSeIFx/wuMJYw+6i6f285"
    "6KEUoOLxmp1o4LKWM2RvStNWQMMLvi0+u118pGTU1Eq3vbqTWgOvs1BBYRvhbEDbKXO9Pb"
    "w7J0N5LeQnLMSr7K81bGTeaA99lzHrOTe9ZFAurGBFGK7ayZ37CVX/YxfTfyU0zlmPu5fz"
    "7SHWwSlD39qdbyG4GwHhAHjq66N2XEhjfmrKvPprX8RsCbsCddLNKDN8TM98Fui/mNRJid"
    "JrYxx3DahmKxfzT19uP9Fnv5OODbCB5wN7uvGbeE78txbkPojGdWJx75pQ/8NsZ9Mw/rj3"
    "MXmybZN7I6PkOTRvKRlsF+dDxLxw77n+yrw8OZXC4ZR3bELbY++Jx1zLj+SDwyJhCC7IYn"
    "m2Y+bvaeZsT6smUguu8QctA4/Cj+A1ebrT62Udgfj4zCxqC3SeYdYIaZUpg+IW7QVxYHz5"
    "0jyCMGz2v+JCbPq3B8iLHzn//pMyLSj8/7bxR4pGX78Ou/MqgrVw3hhYueVtEOcmcZknWy"
    "m8zFxKIt/OxzrgLdiBr4lNsr/h0ldXe9bSDvDxB1clL61xp03MBRFQySukFnzj6SgwQvyu"
    "XLVW6Liy1pLWnfVU1r9KGXD+lX9Yf6DbbBkGpqS+u14K4h7TeurlStWigNqdodaMp1X+nA"
    "aXVIm7d9pdlUu6r2X7VwCfcAUv1Gr7fVr4NqoQzLvyt9pVqoDGmtfdsYtGDZlyFtNTq9bk"
    "+cHQBCqTegX4GhczBfU9uq+MGVcAG6VFv4BT5oN/2GcgWo5yXp0E046Cjt9ubJTEzOsgt1"
    "hH5snH+b4pWoTRmSFsfPy5fGQ45bdwmGYtUkyLfRkR+9F78Aepz+XQ=="
)
