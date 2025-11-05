from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "guild_settings" ALTER COLUMN "funnel_target_channel" TYPE BIGINT USING "funnel_target_channel"::BIGINT;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "guild_settings" ALTER COLUMN "funnel_target_channel" TYPE INT USING "funnel_target_channel"::INT;"""


MODELS_STATE = (
    "eJztWm1zokgQ/isWn/aq9q4SNdH1GxpNON+2lOxLRYsaYYJzgRkXhsRUyv9+PQiCKBqNpP"
    "bCfUil6Bmebp7u6W4aXyRsT7Ch3ZM5dv6SsUP0qVQrvEhoNoP/8VXpc0GiyMYJcXgTrHI0"
    "sfxltBIRauA5dkF4N4ZLG1FkYgMuqWdZIEATlztI5yC5R5aLQTR7AGBsGb4ZoUJiCDSPkl"
    "+euOaOJ7Ya+B55Fo/gluqMaIeQB1aF+MZE05nl2TTCNZgOZhBqRkgmpthBPI7lW6Xx55lv"
    "kUJ5yzcTVnRGxWMQyl3falPs+LN4Xq6Uq6XLchW2+CasJJWFb72rO2TGCaOR3tkznzK60g"
    "KQ0tLmSPtSh29DT5UWi+0PcB/QGHFftBMSVmQJiYE4ioki/h+x4wo7405YEZruhXDLPjfE"
    "4Pf4Irx93RmNKXJSvWGjuWZhanIR2cWLi9dyDyA7uP8mDxo38uATAP4htjEI42X094Kl4n"
    "JNOCgiUpyrjEgMoDMm8Pzs7LQEAmAqgf7aOoFgHMfLU5EFiTH4o4j8e9jvpRH5Wt5uKaze"
    "GUTnnwsWcfl4B4tCn1i2XfeXFSfvU1f+keS10enXhWjGXG46PooPUAeOx2nGLVnWODMxn0"
    "IZCFLFBOkPT8iBKpBMNKuVRH4Rjx8vHNcesYwh5hwodg8sOuv3xmuPKVY0N7b0IWrQ9mir"
    "E3N/HfpSLJZKleJZ6bJ6Ua5ULqpnq4K0uXSiylRXrkVxWgu/96tWBnEF4doTnkwZe9AcPL"
    "Oe92SMUHJ4ykjVdpxLGbMwom/NIROA2eWffr+zljbqSsJbvdtuvQnZ2c8hsInwNSdukL08"
    "me4elqW7sfQWkmNa8pWetzJuMBusz57zmJ7csy4CUNOniFJsZc38hq78so/pu5GfoirH3M"
    "/9/kizsUFQ9vSnasuvB8J8QGxoXTV3xogFb8xZZ59Nbfn1gDtlT5rYpAVviJmfg90a8+uJ"
    "MDoNbGGOoduGZLF/NPX29n6Lvnw0+BaCB9zN7mvGLeH7cpzbEDrjmdWJR37pA7+NcZ/nYu"
    "1x7mDDIPtGVsdHaFJJPsIyOI+2a2rYZv+QfXl45BUrZf3IirhF1wefs04Y1x6JSyYEXJDd"
    "8GRTTT6i994TpVzjyDHxqrJnlGVTdeVl5nia2fbLlkn0vu7voO8QR3kjMLXVHmALhY3Jke"
    "G/MWFvkXkXmGGGFMZUiBuE2uLggX8EecTEf82exMh/5Y4PMe//739zjoj0/fP+BwUeaVm3"
    "/cIrDxvyVVNY4aCnlbeD2Fm6ZJ3sFnMwMWkbP/ucK0A3ojo+5fGKf8BKPV1v+xLiT241cl"
    "L61zqjuIKjMhgEdZN69j6SgwAvFSuXq9gWF1vCWlK/K6raHEATNaJflR/KNzgGI6oqbbXf"
    "hrtGdNC8ulLUWqE8okpvqMrXA7kLrwkj2rodyK2W0lPUn7XCJdwDSI0brdFRvg5rhQps/y"
    "4P5FqhOqL1zm1z2IZtX0a03ez2e33RtAGE3GhCowCKzkF9Xeko4g+uhAnQHnSEXWCDejNo"
    "yleAel6WDj2Ew67c6WxpKsg8Q1dH6Mf6+bdJXonclCFpcfz/263NdusuwVAsmwTxNj7y1w"
    "aLfwHRoXTe"
)
