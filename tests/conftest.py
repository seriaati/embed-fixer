from __future__ import annotations

import importlib
import os
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest_asyncio
from tortoise.contrib.test import tortoise_test_context

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from tortoise.context import TortoiseContext

os.environ.update(DISCORD_TOKEN="test-token", DB_URI="sqlite://:memory:", ENV="dev")
for _key in (
    "SENTRY_DSN",
    "REDIS_URL",
    "PROXY_URL",
    "HEARTBEAT_URL",
    "PIXIV_SESSION_ID",
    "SPONSORS_API_KEY",
):
    os.environ.pop(_key, None)

with patch("dotenv.load_dotenv", return_value=False):
    for _module in (
        "embed_fixer.core.config",
        "embed_fixer.core.db_config",
        "embed_fixer.utils.fetch_info",
    ):
        importlib.import_module(_module)


@pytest_asyncio.fixture
async def db() -> AsyncIterator[TortoiseContext]:
    async with tortoise_test_context(["embed_fixer.models"], app_label="embed_fixer") as context:
        yield context


@pytest_asyncio.fixture(scope="session", loop_scope="session", autouse=True)
async def translations() -> None:
    module = importlib.import_module("embed_fixer.core.translator")
    await module.translator.load()
