from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "guild_settings" ADD "funnel_target_channel" INT;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "guild_settings" DROP COLUMN "funnel_target_channel";"""


MODELS_STATE = (
    "eJzlWltzokoQ/isWT3uq9pxK0ETXNzSacLxtqdlLRYsaYYJzAjMuDImplP/99CAIXpBoJL"
    "UbHlIpeoavm697upvGFwnbE2xo92SOnX8U7BB9KlULLxKazeB/fFX6XJAosvGGOLwJVjma"
    "WP4yWokINfAcuyC8G8OljSgysQGX1LMsEKCJyx2kc5DcI8vFIJo9ADC2DN+MUCExBJpHyS"
    "9PXHPHE1sNfI88i0dwS3VGtEPIA6tCfGOi6czybBrhGkwHMwg1IyQTU+wgHsfyrdL488y3"
    "SKW86ZsJKzqj4jEI5a5vtSl2/C2fl8qlSvGyVIEtvgkrSXnhW+/qDplxwmikd/bMp4yutA"
    "CktLQ50r7U4dvQHUqLxe4HuA9ojLiX7Q0Jk9mGxEAcxUQR/4/YcYWdcSesCE32QrglzQ0x"
    "+BRfhLevO6M+RU6iN2w01yxMTS4iW764eC33ALKH+29Kv36j9D8B4F9iG4MwXkZ/N1iSl2"
    "vCQRGR4lxlRGIAnTGB52dnpyUQABMJ9NfWCQTjOF6eiixIjMEfReS/g143icjX8nZLYfXO"
    "IDr/XLCIy8d7WBT6xLLtur+sOHmfOsqPTV7r7V5NiGbM5abjo/gANeB4nGTckmWNMxPzKZ"
    "SBIFVMkP7whByoApuJZrWykV/E48cLx7VHLGOAOQeK3QOLzvq98dpjihXNjS19iBq0O9pq"
    "xEyvQ19kuVgsy2fFy8pFqVy+qJytCtL20okqU029FsVpLfzer1oZxBWEa094MmXsQXPwzH"
    "pOyRih5PCUkajtOJcyZmFE35pDJgCzzz+9XnstbdTUDW91bzu1BmRnP4fAJsLXnLhF9vJk"
    "uiksS3dj6S0kx7TkKz3vZNxgNlifPecxPblnXQSgpk8RpdjKmvktXfllH9N3Iz9BVY65n/"
    "v9kWZjg6Ds6U/Ull8PhPmA2NC6au6MEQvemLPOPtva8usBd8qeNLFJC94QMz8H+zXm1xNh"
    "dBrYwhxDtw3JIn009fb2foe+fDT4FoIH3M/ua8Yt4ftynNsQOuOZ1YlHfskDv61xn+di7X"
    "HuYMMgaSOr4yN0U0k+wjI4j7Zrathm/5G0PDzy5HJJP7Ii7tD1weesE8a1R+KSCQEXZDc8"
    "2VaTj+i990Qp1zhyTLyq7Bll2URdR1H9+3z4Os3I+mXHgDmtqTvo88JR8RyY2mz1sYXCfu"
    "PIqN4anDfJvAPMMEMKQyXEDSJocfAcP4I8YpC/Zs/GJH/ljg8xxv/zPyVHRPr+ef+DAo+0"
    "LMd+PVUGdeWqIaxw0NPK20HsLF2yTnaTOZiYtIWffc5VoBtRHZ/yeMW/SyWerrd94PAHsh"
    "o5Kf1rDU9cwbFlokE9O43kIMCLcvlyFdviYkdYS8Pv6nDY6ENvNKJf1R/qNzgGIzpUW8Ne"
    "C+4a0X7j6kodVgulEVW7g6Fy3Vc60P2PaPO2rzSbalcd/qwWLuEeQKrfaPW2+nVQLZRh+3"
    "elr1QLlRGttW8bgxZs+zKirUan1+2JXgwglHoD6j8oOgf1NbWtij+4EiZA1W8Lu8CG4U2/"
    "oVwB6nlJOvQQDjpKu72jVyDzDF0dof/h7UCcsvj5z4K0OH5evtwe0m7dbTAUyyZBvI2P/B"
    "HB4n9nFGq3"
)
