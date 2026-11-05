from __future__ import annotations

import runpy
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from aiohttp import web

from embed_fixer.cogs import health as cog_module
from embed_fixer.cogs.health import HealthCheck
from embed_fixer.core.config import settings

if TYPE_CHECKING:
    from aiohttp.pytest_plugin import AiohttpServer


async def test_health_cog_without_url_has_no_session_or_loop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cog_module, "HEARTBEAT_URL", None)
    cog = HealthCheck(MagicMock())
    with (
        patch.object(cog.send_heartbeat, "start") as start,
        patch.object(cog.send_heartbeat, "cancel") as cancel,
    ):
        await cog.cog_load()
        await cog.send_heartbeat()
        await cog.cog_unload()
    assert cog.session is None
    start.assert_not_called()
    cancel.assert_not_called()


@pytest.mark.parametrize("status", [200, 503])
async def test_health_cog_load_ping_and_unload_real_http(
    aiohttp_server: AiohttpServer, monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    calls: list[str] = []

    async def heartbeat(request: web.Request) -> web.Response:
        await request.read()
        calls.append(request.path)
        return web.Response(status=status)

    app = web.Application()
    app.router.add_get("/heartbeat", heartbeat)
    server = await aiohttp_server(app)
    monkeypatch.setattr(cog_module, "HEARTBEAT_URL", str(server.make_url("/heartbeat")))
    cog = HealthCheck(MagicMock())
    with (
        patch.object(cog.send_heartbeat, "start") as start,
        patch.object(cog.send_heartbeat, "cancel") as cancel,
        patch.object(cog_module.logger, "error") as error,
    ):
        await cog.cog_load()
        assert cog.session is not None
        assert not cog.session.closed
        try:
            await cog.send_heartbeat()
        finally:
            await cog.cog_unload()
    assert cog.session.closed
    assert calls == ["/heartbeat"]
    start.assert_called_once_with()
    cancel.assert_called_once_with()
    if status == 200:
        error.assert_not_called()
    else:
        error.assert_called_once_with("Heartbeat ping returned non-200 status code: 503")


async def test_health_cog_heartbeat_transport_failure_is_logged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cog_module, "HEARTBEAT_URL", "https://heartbeat.invalid")
    cog = HealthCheck(MagicMock())
    cog.session = MagicMock(spec=aiohttp.ClientSession)
    cog.session.get.side_effect = aiohttp.ClientConnectionError("offline")
    with patch.object(cog_module.logger, "error") as error:
        await cog.send_heartbeat()
    error.assert_called_once_with("Error sending heartbeat ping: offline")


async def test_health_cog_waits_for_ready_before_loop() -> None:
    bot = MagicMock()
    bot.wait_until_ready = AsyncMock()
    cog = HealthCheck(bot)
    await cog.before_send_heartbeat()
    bot.wait_until_ready.assert_awaited_once_with()


async def test_health_cog_setup_registers_with_bot() -> None:
    bot = MagicMock()
    bot.add_cog = AsyncMock()
    await cog_module.setup(bot)
    assert bot.add_cog.await_args is not None
    cog = bot.add_cog.await_args.args[0]
    assert isinstance(cog, HealthCheck)
    assert cog.bot is bot


def test_health_cog_import_with_configured_heartbeat(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "heartbeat_url", "https://heartbeat.invalid")
    with patch("loguru.logger") as logger:
        namespace = runpy.run_path(
            "embed_fixer/cogs/health.py", run_name="configured_heartbeat_probe"
        )
    assert namespace["HEARTBEAT_URL"] == "https://heartbeat.invalid"
    logger.warning.assert_not_called()
