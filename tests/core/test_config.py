from __future__ import annotations

from typing import TYPE_CHECKING, cast

import pytest
from pydantic import ValidationError

from embed_fixer.core.config import Settings

if TYPE_CHECKING:
    from typing import Any


@pytest.mark.parametrize("session_id", [None, "fixture-session"])
def test_pixiv_headers_include_authentication_only_when_configured(session_id: str | None) -> None:
    settings = Settings(
        discord_token="fixture-token",
        db_uri="sqlite://:memory:",
        user_agent="test-agent",
        pixiv_session_id=session_id,
    )
    assert settings.pixiv_headers["Referer"] == "https://www.pixiv.net/"
    assert settings.pixiv_headers["User-Agent"] == "test-agent"
    assert settings.pixiv_headers.get("Cookie") == (
        None if session_id is None else "PHPSESSID=fixture-session"
    )


@pytest.mark.parametrize("environment", ["dev", "prod"])
def test_settings_reads_environment_without_optional_services(
    monkeypatch: pytest.MonkeyPatch, environment: str
) -> None:
    monkeypatch.setenv("ENV", environment)
    monkeypatch.setenv("DISCORD_TOKEN", "fixture-token")
    monkeypatch.setenv("DB_URI", "sqlite://:memory:")
    settings = cast("Any", Settings)()
    assert settings.env == environment
    assert settings.discord_token == "fixture-token"
    assert settings.db_uri == "sqlite://:memory:"
    assert settings.redis_url is None
    assert settings.sponsors_api_key is None
    assert settings.sentry_dsn is None


def test_unknown_environment_is_rejected() -> None:
    with pytest.raises(ValidationError, match="env"):
        Settings.model_validate(
            {"discord_token": "fixture-token", "db_uri": "sqlite://:memory:", "env": "staging"}
        )


def test_required_configuration_values_are_validated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DISCORD_TOKEN")
    monkeypatch.delenv("DB_URI")
    with pytest.raises(ValidationError) as error:
        cast("Any", Settings)()
    assert {entry["loc"] for entry in error.value.errors()} == {("discord_token",), ("db_uri",)}
