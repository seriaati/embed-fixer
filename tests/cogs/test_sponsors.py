from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from embed_fixer.cogs import sponsors
from tests.support.cogs import bot

if TYPE_CHECKING:
    from typing import Any


@pytest.mark.parametrize("enabled", [False, True])
async def test_sponsors_lifecycle_refresh_and_ready_wait(
    monkeypatch: pytest.MonkeyPatch, *, enabled: bool
) -> None:
    manager = MagicMock(enabled=enabled, refresh=AsyncMock(), revalidate_guilds=AsyncMock())
    monkeypatch.setattr(sponsors, "sponsors", manager)
    client = bot()
    cog: Any = sponsors.SponsorsCog(client)
    start = MagicMock()
    cancel = MagicMock()
    monkeypatch.setattr(cog._refresh_sponsors, "start", start)
    monkeypatch.setattr(cog._refresh_sponsors, "cancel", cancel)
    await cog.cog_load()
    assert start.call_count == int(enabled)
    await cog._refresh_sponsors()
    manager.refresh.assert_awaited_once_with(client.session)
    manager.revalidate_guilds.assert_awaited_once_with(client)
    await cog._before_refresh_sponsors()
    client.wait_until_ready.assert_awaited_once()
    await cog.cog_unload()
    cancel.assert_called_once()


@pytest.mark.parametrize("module", [sponsors])
async def test_cog_setup_registers_expected_cog(module: Any) -> None:
    client = bot()
    await module.setup(client)
    assert client.add_cog.await_count == 1
    assert client.add_cog.await_args.args[0].bot is client
