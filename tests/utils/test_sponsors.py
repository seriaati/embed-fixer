from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import discord
import pytest
from aiohttp import web

from embed_fixer.core.config import settings
from embed_fixer.models import SponsoredGuild
from embed_fixer.utils import sponsors as sponsors_module
from embed_fixer.utils.sponsors import QUERY_MEMBERS_LIMIT, SponsorManager

if TYPE_CHECKING:
    from aiohttp.pytest_plugin import AiohttpServer

pytestmark = pytest.mark.usefixtures("db")


@pytest.fixture(autouse=True)
def sponsors_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "sponsors_api_key", "sponsors-test-key")


def guild_with_members(guild_id: int, members: list[SimpleNamespace]) -> MagicMock:
    guild = MagicMock(spec=discord.Guild)
    guild.id = guild_id
    guild.query_members = AsyncMock(return_value=members)
    return guild


def sponsor_member(sponsor_id: int, *, administrator: bool) -> SimpleNamespace:
    return SimpleNamespace(
        id=sponsor_id, guild_permissions=SimpleNamespace(administrator=administrator)
    )


async def test_self_hosted_mode_unlocks_every_guild_without_fetching(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "sponsors_api_key", None)
    manager = SponsorManager()
    session = MagicMock(spec=aiohttp.ClientSession)
    guild = guild_with_members(1, [])
    assert not manager.enabled
    await manager.refresh(session)
    assert await manager.unlock_guild(guild)
    assert await manager.is_guild_unlocked(1)
    assert await SponsoredGuild.all().count() == 0
    session.get.assert_not_called()
    guild.query_members.assert_not_awaited()


async def test_refresh_real_http_replaces_sponsors_and_authenticates(
    aiohttp_server: AiohttpServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen_keys: list[str] = []
    payload = [{"id": "1"}, {"id": "2"}, {"id": "2"}]

    async def respond(request: web.Request) -> web.Response:
        await request.read()
        seen_keys.append(request.headers["x-api-key"])
        return web.json_response(payload)

    app = web.Application()
    app.router.add_get("/sponsors", respond)
    server = await aiohttp_server(app)
    monkeypatch.setattr(sponsors_module, "SPONSORS_API_URL", str(server.make_url("/sponsors")))
    manager = SponsorManager()
    manager._sponsor_ids = {99}
    assert manager.enabled
    async with aiohttp.ClientSession() as session:
        await manager.refresh(session)
        assert manager._sponsor_ids == {1, 2}
        payload.clear()
        await manager.refresh(session)
    assert manager._sponsor_ids == set()
    assert seen_keys == ["sponsors-test-key", "sponsors-test-key"]


@pytest.mark.parametrize("status", [401, 503])
async def test_refresh_http_failure_retains_previous_sponsors(
    aiohttp_server: AiohttpServer, monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    async def respond(request: web.Request) -> web.Response:
        await request.read()
        return web.json_response({"error": "unavailable"}, status=status)

    app = web.Application()
    app.router.add_get("/sponsors", respond)
    server = await aiohttp_server(app)
    monkeypatch.setattr(sponsors_module, "SPONSORS_API_URL", str(server.make_url("/sponsors")))
    manager = SponsorManager()
    manager._sponsor_ids = {99}
    with patch.object(sponsors_module, "capture_exception") as capture:
        async with aiohttp.ClientSession() as session:
            await manager.refresh(session)
    assert manager._sponsor_ids == {99}
    assert isinstance(capture.call_args.args[0], aiohttp.ClientResponseError)


async def test_refresh_connection_failure_retains_initial_unknown_state() -> None:
    manager = SponsorManager()
    session = MagicMock(spec=aiohttp.ClientSession)
    failure = aiohttp.ClientConnectionError("offline")
    session.get.side_effect = failure
    with patch.object(sponsors_module, "capture_exception") as capture:
        await manager.refresh(session)
    assert manager._sponsor_ids is None
    capture.assert_called_once_with(failure)


@pytest.mark.parametrize("ids", [None, set()])
async def test_find_admin_sponsor_without_loaded_sponsors(ids: set[int] | None) -> None:
    manager = SponsorManager()
    manager._sponsor_ids = ids
    guild = guild_with_members(1, [])
    assert await manager.find_admin_sponsor(guild) is None
    guild.query_members.assert_not_awaited()


async def test_find_admin_sponsor_requires_administrator() -> None:
    manager = SponsorManager()
    manager._sponsor_ids = {1, 2}
    guild = guild_with_members(
        5, [sponsor_member(1, administrator=False), sponsor_member(2, administrator=True)]
    )
    assert await manager.find_admin_sponsor(guild) == 2
    assert set(guild.query_members.await_args.kwargs["user_ids"]) == {1, 2}
    assert guild.query_members.await_args.kwargs["limit"] == QUERY_MEMBERS_LIMIT


async def test_find_admin_sponsor_batches_discord_queries() -> None:
    manager = SponsorManager()
    manager._sponsor_ids = set(range(205))
    guild = guild_with_members(1, [])
    guild.query_members.side_effect = [[], [sponsor_member(100, administrator=False)], []]
    assert await manager.find_admin_sponsor(guild) is None
    batches = [call.kwargs["user_ids"] for call in guild.query_members.await_args_list]
    assert [len(batch) for batch in batches] == [100, 100, 5]
    assert set().union(*map(set, batches)) == manager._sponsor_ids
    assert all(call.kwargs["limit"] == 100 for call in guild.query_members.await_args_list)


async def test_unlock_guild_persists_and_replaces_administrator_sponsor() -> None:
    manager = SponsorManager()
    manager._sponsor_ids = {1, 2}
    guild = guild_with_members(42, [sponsor_member(1, administrator=True)])
    assert await manager.unlock_guild(guild)
    assert await manager.is_guild_unlocked(42)
    assert (await SponsoredGuild.get(id=42)).sponsor_id == 1
    guild.query_members.return_value = [sponsor_member(2, administrator=True)]
    assert await manager.unlock_guild(guild)
    assert (await SponsoredGuild.get(id=42)).sponsor_id == 2
    assert await SponsoredGuild.all().count() == 1


async def test_unlock_without_admin_sponsor_does_not_create_record() -> None:
    manager = SponsorManager()
    manager._sponsor_ids = {1}
    guild = guild_with_members(42, [sponsor_member(1, administrator=False)])
    assert not await manager.unlock_guild(guild)
    assert not await manager.is_guild_unlocked(42)
    assert await SponsoredGuild.all().count() == 0


async def test_locked_and_removed_guilds() -> None:
    manager = SponsorManager()
    await SponsoredGuild.create(id=1, sponsor_id=None)
    await SponsoredGuild.create(id=2, sponsor_id=22)
    assert not await manager.is_guild_unlocked(1)
    assert await manager.is_guild_unlocked(2)
    await manager.remove_guild(2)
    await manager.remove_guild(2)
    assert not await manager.is_guild_unlocked(2)
    assert (await SponsoredGuild.get(id=1)).sponsor_id is None


async def test_revalidate_without_successful_refresh_preserves_database() -> None:
    await SponsoredGuild.create(id=1, sponsor_id=10)
    bot = MagicMock(spec=discord.Client)
    await SponsorManager().revalidate_guilds(bot)
    bot.get_guild.assert_not_called()
    assert (await SponsoredGuild.get(id=1)).sponsor_id == 10


async def test_revalidate_unlocks_relocks_skips_missing_and_retains_failed_guilds() -> None:
    for guild_id, sponsor_id in [(1, None), (2, 10), (3, 10), (4, 10), (5, 10)]:
        await SponsoredGuild.create(id=guild_id, sponsor_id=sponsor_id)
    guilds = {
        1: guild_with_members(1, [sponsor_member(20, administrator=True)]),
        2: guild_with_members(2, []),
        3: guild_with_members(3, [sponsor_member(10, administrator=True)]),
        4: guild_with_members(4, []),
    }
    failure = discord.ClientException("members unavailable")
    guilds[4].query_members.side_effect = failure
    bot = MagicMock(spec=discord.Client)
    bot.get_guild.side_effect = guilds.get
    manager = SponsorManager()
    manager._sponsor_ids = {10, 20}
    with patch.object(sponsors_module, "capture_exception") as capture:
        await manager.revalidate_guilds(bot)
    assert {guild.id: guild.sponsor_id for guild in await SponsoredGuild.all()} == {
        1: 20,
        2: None,
        3: 10,
        4: 10,
        5: 10,
    }
    capture.assert_called_once_with(failure)


async def test_revalidate_empty_sponsor_list_relocks_guilds() -> None:
    await SponsoredGuild.create(id=1, sponsor_id=10)
    manager = SponsorManager()
    manager._sponsor_ids = set()
    bot = MagicMock(spec=discord.Client)
    guild = guild_with_members(1, [])
    bot.get_guild.return_value = guild
    await manager.revalidate_guilds(bot)
    assert (await SponsoredGuild.get(id=1)).sponsor_id is None
    guild.query_members.assert_not_awaited()
