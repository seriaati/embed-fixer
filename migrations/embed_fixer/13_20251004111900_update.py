from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


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


MODELS_STATE = (
    "eJztWm1v4jgQ/ison/akvVObQunyLVDo5nirIN3dU6kiQ9zga2KzidNSVfz3G+eFhECgBb"
    "JXNfsBocw4M+NnxjPj2C8StsfY0O/JHDt/Kdghk6lUK71IaDaD/yRX+lySKLJxihy9BFyO"
    "xpbPRksSoQaeYxeIt3fwaCOKTGzAI/UsCwho7HIHTThQ7pHlYiDNHkAwtgzfjEghMYQ0j5"
    "KfnnjmjieGGvgeeRaPxQXqjHiEoIdWRfKNsT5hlmfTWK7BJmAGoWYsycQUO4gnZflW6fx5"
    "5lukUt7yzQTOhFExDUK561ttihF/yqflavni7Lx8AUN8E5aU6sK33p04ZMYJo7He2TOfMr"
    "rUAiKlwOZYe6DDt6GnSYvF5gnchzDG2Mt2isJklqIYiKMEKcb/ETuusDPphCWg2V6Ihuxy"
    "Q0L8Dl9Er686ozFFTqY3bDTXLUxNLiJbrlReiz0I2YL9N2XQ+KoMPoHAP8QwBmEcRH8vZM"
    "kBTzgoBlKsq5xADEXnDODpyclxAQSBmQD6vFUAwTiOg1WRB4gJ8XsB+few38sC8rW43VDg"
    "3hpkwj+XLOLyuy0oCn2CbbvuTysJ3qeu8iONa6PTrwvSjLncdHwpvoA6YHyXZVyAss6Zif"
    "kUykCYKsZo8vCEHKgC6USz5KTyi5h+snBcecQyWmTeBbnMeGPVSb2crD6mYPnD3N8l6N2U"
    "oBhI3z/HXL+vW6cwJQNbmAf5Thk2lMumsMJBT0tvh7ETuGQV7BZzMDFpGz/7mKsAN6ITfM"
    "AyXwvnIeYcpuFq/gSjOIlkh1GwOLiWG8wGeTo5qg+SEb2iYK8sCpHdpJ69C+kwys/k6vky"
    "wMXDhtiWtO+qpjUHUMBG9Fr9oX6DtTCimtrW+m14a0QHzctLVauVyiOq9oaacjVQurVSZU"
    "RbNwOl1VJ7qvZPrXQO74Ckxle90VGvh7VSFYZ/VwZKrXQxovXOTXPYhmFfRrTd7PZ7fVEw"
    "QYTSaNb7QtEpqK+rHVX84EmYcNOtd4RdYIP2ddBULkHqKVhxrYE1pxXprUty2FU6nWhdxm"
    "6HQMvR57H0fR3+blJZKlPlCFpS/l6w1Ym5G7kvsnx2VpVPzs4vKuVqtXJxsoRwnXUkLOvq"
    "lYBzpf0I8H1Ln3GbQiiRVsJ4uztiKxKl3761VzOSfH29HXFD7ofpSD5MQL6idzm85BJXAK"
    "4/4fGUsQfdwTPreUdWiSh71N8sbfu5lDELI3ropmYMYrb5p9/vrOxj6mrKWz2ok03YLvqb"
    "GhhE+IoT18BObAG2oCzd3kmHgJzQUqz94kbEgxSdP+YJPYVHXQSgPpkiSrGVN/JruoqLPq"
    "a/DPwMVQXGfu73R7qNDYLyhz9TW3E9EOUDYkPrqrszRizs5J591rUV1wPulD3pYpAefrLO"
    "fR1s11hcT0TRGXxdhG4bksXus7LD2/sN+orR4FsIJrgd3dd8kon2y0lsI9E5H6Id+Qwy+w"
    "Ry7fzRc7H+OHewYZBdZ2j7R2haSTHCMlyPtmvq2Gb/kl15eOTJ1fJkz4q4QdcHP/gdM64/"
    "EpeMCbggv48n62qKEb33nijlOkeOiZeVPacsm6mrON8cY+CfpuAT0bjoDhM9rpFbA7dZU3"
    "EbN7CZuhbMM4rEHBuLTF0fttPwtwvMISahyNItQh/0Mc+vK85W93Hz9/90Z2f1nsIBR2XL"
    "iw4Zh2X6o/z7vOz91a5fcF4GjF1V8GWxZ+scyi5W3TtOqnjZsKZ3tSs5XOVKraHQ1FZ7gK"
    "HChp9CjnUpa+WOYeaFrMz8ufgPztszdQ=="
)
