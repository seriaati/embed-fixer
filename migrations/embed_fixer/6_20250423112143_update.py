from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "guild_settings" ADD "enable_fix_channels" JSONB NOT NULL DEFAULT '[]';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "guild_settings" DROP COLUMN "enable_fix_channels";"""


MODELS_STATE = (
    "eJzlWW1zokgQ/isWn/aq9q4SNNH1GxpNON+2lOzuVUxRI0xwLjC4MGxMpfzv28OLIIpEIq"
    "m7+MGy6B6ebp7u6R6aFwFbM6yrD2SJnb8k7BBtLjQrLwJaLOA/qRU+VwSKLJwSRzeBlqGZ"
    "6avRWkSojpfYBeHdPVxaiCID63BJPdMEAZq5zEEaA8kDMl0MosUjAGNT992IDBKdo3mU/P"
    "T4NXM8vlTHD8gzWQwXmNPjFVweehXh6zNVs03PojGubmvgBqFGjGRgih3Ekli+Vyp7Xvge"
    "yZR1fTdBo9mUPwahzPW9NviKP8XzWr3WqF7WGrDEd2Etqa98713NIQtGbBrbXTyzuU3XVg"
    "BSCHyOrQc2fB+GirBa7X6Ah5DGmHvRSkls0U5JdMRQQhTz/ws7LvczGYQ1odlRiJbkhSEB"
    "nxOL6PbNYLTnyMmMhoWWqompwXhmixcXr+UeQPZw/00at2+k8ScA/IMvsyGNg+wfhiox0P"
    "EAxUTyfVUSiSF0yQSen50dl0AAzCTQ120SCM4xHOyKMkhMwBci8u/JaJhF5Gt5u6WgvdOJ"
    "xj5XTOKy+z0scntcbbnuTzNJ3qeB9CPNa7s/anHRwnaZ4fgoPkALOL7Pci5gWWW2gdkc2k"
    "BYKmZIe3xCDnSBdKFZa1L1hT9+snFce8TUJ5gxoNg9sOls3pvsPQbXqG5C9SF60O5saxEj"
    "vw99EcVqtS6eVS8bF7V6/aJxtm5I26ojdaaWfM2b00b6vV+30onLCVef8Gxu24+qgxfmc0"
    "7FiCSHl4xMa8VCatsmRvStNWQGMPviMxr1N8pGS05Fa3g7aHWgOvs1BBYRthHELbKDnenm"
    "sCzc3QtvITlh5bTK807GddsC78vnPGHn5FnnCahqc0QpNstmfsvW6bKP6buRn2HqhLlf+u"
    "cj1cI6QeXTn2ntdCMQ1QNiwdFVdRc2MeGNuezqs23tdCPgzu0nlS9SwzfE0vfBfounG4ko"
    "O3VsYobhtA3FIn809fbj/Q57p3HANxE84H52XzNuid6Xk9xG0CXPrI488sse+G2N+zwXq7"
    "+WDtZ1kjeyKp6haSOnkZbhfrRcQ8WW/S/Jq8NTT6zXtIIdcYetDzhnPc4M8GXHxC6vSx40"
    "ry2U3qGr3d4Ymygq4AWTfGsS2SXLATBj60KUORFuWPhWBw9GY8gCk9ENf1Kj0XU4PsRc9P"
    "//bS4m0o/P+28UeKSgvvkFSpq0pasO98JBT+toh7kThGST7K7tYGLQHn72OZeBbkQ1fMzt"
    "lRz0Z+6ut02M/QmXSo5K/0YHSRooVMEgqTvUs/JIDhO8KtYv17nNL3aktaB8lxWlM4ZmM6"
    "Vf5R/yN9gGU6rIPWXUg7umdNy5upKVZqU2pfJwokjXY2kAx6kp7d6OpW5XHsrKP83KJdwD"
    "SO0btd2Xv06alTos/y6NpWalMaWt/m1n0oNlX6a01xmMhiPe3ABCanfgOACGzsF8S+7L/A"
    "dX3AU4BPS5X+CDcjPuSFeAel4TDt2Ek4HU728fHfhop7xQx+hF4/yfKV6p2lQiaUn8U/kU"
    "dshx6y7FUKKahPl2X/Cr7Oo3H4yNTA=="
)
