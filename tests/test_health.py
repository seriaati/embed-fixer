from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import aiohttp
import pytest

from embed_fixer.health import HealthCheckServer


def sharded_bot(closed_shards: list[bool]) -> MagicMock:
    bot = MagicMock()
    bot.shards = {
        index: SimpleNamespace(is_closed=MagicMock(return_value=closed))
        for index, closed in enumerate(closed_shards)
    }
    return bot


def listening_url(server: HealthCheckServer) -> str:
    assert server.runner is not None
    address = server.runner.addresses[0]
    assert isinstance(address, tuple)
    return f"http://127.0.0.1:{address[1]}/health"


@pytest.mark.parametrize(
    ("closed_shards", "status", "body"),
    [
        ([], 503, "Not Ready"),
        ([True], 503, "Not Ready"),
        ([False, True], 503, "Not Ready"),
        ([False, False], 200, "OK"),
    ],
)
async def test_health_server_real_http_reports_shard_readiness(
    closed_shards: list[bool], status: int, body: str
) -> None:
    server = HealthCheckServer(sharded_bot(closed_shards))
    await server.start(port=0)
    try:
        async with (
            aiohttp.ClientSession() as session,
            session.get(listening_url(server)) as response,
        ):
            assert response.status == status
            assert await response.text() == body
    finally:
        await server.stop()
    assert server.runner is not None
    assert server.runner.addresses == []


async def test_health_server_context_starts_and_stops_on_exception() -> None:
    server = HealthCheckServer(sharded_bot([False]))
    original_start = server.start

    async def start_ephemeral() -> None:
        await original_start(port=0)

    async def fail_context() -> None:
        async with server as active:
            assert active is server
            assert server.runner is not None
            assert server.runner.addresses
            message = "context failure"
            raise RuntimeError(message)

    with (
        patch.object(server, "start", side_effect=start_ephemeral),
        pytest.raises(RuntimeError, match="context failure"),
    ):
        await fail_context()
    assert server.runner is not None
    assert server.runner.addresses == []


async def test_health_server_stop_before_start_is_safe() -> None:
    server = HealthCheckServer(sharded_bot([]))
    await server.stop()
    assert server.site is None
    assert server.runner is None
