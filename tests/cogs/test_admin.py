from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from embed_fixer.cogs import admin
from tests.support.cogs import bot
from tests.support.ui import interaction

if TYPE_CHECKING:
    from typing import Any


async def test_admin_owner_guard_and_sync_response() -> None:
    client = bot()
    client.tree.sync = AsyncMock(return_value=[object(), object()])
    cog: Any = admin.Admin(client)
    ctx = interaction()
    message = MagicMock(edit=AsyncMock())
    ctx.send = AsyncMock(return_value=message)
    assert await cog.cog_check(ctx)
    client.is_owner.assert_awaited_once_with(ctx.author)
    client.is_owner.return_value = False
    assert not await cog.cog_check(ctx)
    await cog.sync_command.callback(cog, ctx)
    ctx.send.assert_awaited_once_with("Syncing commands...")
    message.edit.assert_awaited_once_with(content="Synced 2 commands.")


@pytest.mark.parametrize("module", [admin])
async def test_cog_setup_registers_expected_cog(module: Any) -> None:
    client = bot()
    await module.setup(client)
    assert client.add_cog.await_count == 1
    assert client.add_cog.await_args.args[0].bot is client
