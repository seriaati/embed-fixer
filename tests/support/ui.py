from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import discord


def interaction(*, guild_id: int | None = 100, user_id: int = 200) -> Any:
    value = MagicMock()
    value.guild_id = guild_id
    value.guild = guild(guild_id) if guild_id is not None else None
    value.user.id = user_id
    value.response.is_done.return_value = False
    value.response.defer = AsyncMock()
    value.response.edit_message = AsyncMock()
    value.response.send_message = AsyncMock()
    value.response.send_modal = AsyncMock()
    value.followup.send = AsyncMock()
    value.edit_original_response = AsyncMock()
    value.original_response = AsyncMock()
    return value


def guild(guild_id: int = 100, *, channel_ids: tuple[int, ...] = ()) -> Any:
    value = MagicMock()
    value.id = guild_id
    value.preferred_locale = discord.Locale.american_english
    value.by_category.return_value = [(None, [MagicMock(id=cid) for cid in channel_ids])]
    value.threads = []
    value.roles = []
    return value


def emojis() -> Any:
    return {"ARROW_BACK": "⬅️", "ARROW_FORWARD": "➡️"}
