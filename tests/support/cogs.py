from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

from tests.support.ui import emojis


def bot() -> Any:
    value = MagicMock()
    value.app_emojis = emojis()
    value.add_cog = AsyncMock()
    value.is_owner = AsyncMock(return_value=True)
    value.wait_until_ready = AsyncMock()
    return value
