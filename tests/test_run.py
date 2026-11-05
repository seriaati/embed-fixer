from __future__ import annotations

import asyncio
import runpy
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import aiohttp
import discord
import pytest
from discord.ext.commands import CommandNotFound
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

import run as runtime
from embed_fixer.core.config import settings

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from types import TracebackType

    from sentry_sdk.types import Event


@dataclass
class StartupResource:
    name: str
    events: list[str]
    failure: BaseException | None = None

    async def __aenter__(self) -> StartupResource:
        self.events.append(f"enter:{self.name}")
        return self

    async def __aexit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        self.events.append(f"exit:{self.name}")

    async def start(self, token: str) -> None:
        self.events.append(f"start:{token}")
        if self.failure is not None:
            raise self.failure


@pytest.mark.parametrize("env", ["dev", "prod"])
def test_setup_logger_configures_console_standard_logging_and_rotated_file(
    monkeypatch: pytest.MonkeyPatch, env: str
) -> None:
    monkeypatch.setattr(settings, "env", env)
    with (
        patch.object(runtime, "logger") as logger,
        patch.object(runtime.logging, "basicConfig") as configure,
    ):
        runtime.setup_logger()
    logger.disable.assert_called_once_with("aiohttp.web_log")
    logger.remove.assert_called_once_with()
    assert logger.add.call_args_list[0].args == (sys.stderr,)
    assert logger.add.call_args_list[0].kwargs == {"level": "INFO" if env == "prod" else "DEBUG"}
    assert logger.add.call_args_list[1].args == ("logs/embed_fixer.log",)
    assert logger.add.call_args_list[1].kwargs == {
        "level": "DEBUG",
        "rotation": "1 week",
        "retention": "2 weeks",
    }
    assert configure.call_args.kwargs["force"] is True
    assert configure.call_args.kwargs["level"] == runtime.logging.INFO
    assert isinstance(configure.call_args.kwargs["handlers"][0], runtime.InterceptHandler)


@pytest.mark.parametrize(
    ("exception_type", "status", "expected"),
    [
        (discord.DiscordServerError, 503, True),
        (discord.DiscordServerError, 500, False),
        (discord.HTTPException, 503, False),
    ],
)
def test_discord_503_filter_uses_exception_type_and_status(
    exception_type: type[discord.HTTPException], status: int, expected: bool
) -> None:
    response = MagicMock(spec=aiohttp.ClientResponse)
    response.status = status
    response.reason = "Service unavailable"
    failure = exception_type(response, {"message": "Upstream unavailable", "code": 0})
    hint = {"exc_info": (type(failure), failure, None)}
    assert runtime._is_discord_503(hint, {}) is expected


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ([], False),
        ([{"type": "DiscordServerError", "value": "503 Service Unavailable"}], True),
        ([{"type": "DiscordServerError", "value": "500 Internal Error"}], False),
        ([{"type": "DiscordServerError", "value": None}], False),
        ([{"type": "HTTPException", "value": "503 Service Unavailable"}], False),
        (
            [
                {"type": "ValueError", "value": "unrelated"},
                {"type": "DiscordServerError", "value": "503 Service Unavailable"},
            ],
            True,
        ),
    ],
)
def test_discord_503_filter_serialized_event_fallback(
    values: list[dict[str, object]], expected: bool
) -> None:
    assert runtime._is_discord_503({}, {"exception": {"values": values}}) is expected


def test_before_send_drops_discord_503_and_preserves_other_event_identity() -> None:
    transient: Event = {
        "exception": {
            "values": [{"type": "DiscordServerError", "value": "503 Service Unavailable"}]
        }
    }
    normal: Event = {"message": "A relevant error"}
    assert runtime.before_send(transient, {}) is None
    assert runtime.before_send(normal, {}) is normal


def test_setup_sentry_without_dsn_does_not_initialize(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "sentry_dsn", None)
    with patch.object(runtime.sentry_sdk, "init") as initialize:
        runtime.setup_sentry()
    initialize.assert_not_called()


def test_setup_sentry_sets_integrations_release_and_error_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "sentry_dsn", "https://public@localhost/1")
    monkeypatch.setattr(settings, "env", "prod")
    with (
        patch.object(runtime.sentry_sdk, "init") as initialize,
        patch.object(runtime, "get_project_version", return_value="v1.2.3"),
    ):
        runtime.setup_sentry()
    options = initialize.call_args.kwargs
    assert options["dsn"] == "https://public@localhost/1"
    assert options["environment"] == "prod"
    assert options["release"] == "v1.2.3"
    assert options["enable_logs"] is True
    assert options["ignore_errors"] == [CommandNotFound]
    assert options["before_send"] is runtime.before_send
    assert len(options["integrations"]) == 1
    assert isinstance(options["integrations"][0], AsyncioIntegration)
    assert len(options["disabled_integrations"]) == 1
    assert isinstance(options["disabled_integrations"][0], LoggingIntegration)


@pytest.mark.parametrize("redis_url", [None, "redis://localhost:6379/0"])
@pytest.mark.parametrize(
    "failure", [None, KeyboardInterrupt(), asyncio.CancelledError(), RuntimeError("startup failed")]
)
async def test_main_selects_cache_starts_bot_and_closes_resources(
    monkeypatch: pytest.MonkeyPatch, redis_url: str | None, failure: BaseException | None
) -> None:
    monkeypatch.setattr(settings, "redis_url", redis_url)
    monkeypatch.setattr(settings, "env", "dev")
    monkeypatch.setattr(settings, "discord_token", "isolated-test-token")
    events: list[str] = []
    session = StartupResource("session", events)
    bot = StartupResource("bot", events, failure)
    health = StartupResource("health", events)
    with (
        patch.object(runtime, "wrap_task_factory") as wrap,
        patch.object(runtime, "SQLiteBackend") as sqlite,
        patch.object(runtime, "RedisBackend") as redis,
        patch.object(runtime, "CachedSession", return_value=session) as session_factory,
        patch.object(runtime, "EmbedFixer", return_value=bot) as bot_factory,
        patch.object(runtime, "HealthCheckServer", return_value=health) as health_factory,
    ):
        if isinstance(failure, RuntimeError):
            with pytest.raises(RuntimeError, match="startup failed"):
                await runtime.main()
        else:
            await runtime.main()
    wrap.assert_called_once_with()
    if redis_url is None:
        sqlite.assert_called_once_with(expire_after=runtime.EXPIRE_AFTER)
        redis.assert_not_called()
        backend = sqlite.return_value
    else:
        redis.assert_called_once_with(expire_after=runtime.EXPIRE_AFTER, address=redis_url)
        sqlite.assert_not_called()
        backend = redis.return_value
    session_factory.assert_called_once_with(cache=backend, headers=runtime.HEADERS)
    bot_factory.assert_called_once_with(session=session, env="dev")
    health_factory.assert_called_once_with(bot)
    assert events == [
        "enter:session",
        "enter:bot",
        "enter:health",
        "start:isolated-test-token",
        "exit:health",
        "exit:bot",
        "exit:session",
    ]


@pytest.mark.parametrize("has_uvloop", [False, True])
def test_script_entrypoint_selects_available_event_loop(
    monkeypatch: pytest.MonkeyPatch, has_uvloop: bool
) -> None:
    monkeypatch.setattr(settings, "sentry_dsn", None)
    monkeypatch.setattr(discord.VoiceClient, "warn_nacl", True)
    consumed: list[str] = []

    def consume(coro: Coroutine[Any, Any, None]) -> None:
        consumed.append(coro.__name__)
        coro.close()

    uvloop = MagicMock()
    uvloop.run.side_effect = consume
    monkeypatch.setitem(sys.modules, "uvloop", uvloop if has_uvloop else None)
    with (
        patch("loguru.logger"),
        patch("logging.basicConfig"),
        patch("asyncio.run", side_effect=consume) as asyncio_run,
    ):
        runpy.run_path("run.py", run_name="__main__")
    assert consumed == ["main"]
    assert discord.VoiceClient.warn_nacl is False
    if has_uvloop:
        uvloop.run.assert_called_once()
        asyncio_run.assert_not_called()
    else:
        asyncio_run.assert_called_once()
