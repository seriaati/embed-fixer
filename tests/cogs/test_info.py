from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from embed_fixer.cogs import info
from tests.support.cogs import bot
from tests.support.ui import interaction

if TYPE_CHECKING:
    from typing import Any


@pytest.mark.usefixtures("db")
async def test_info_command_builds_translated_embed_image() -> None:
    cog: Any = info.InfoCog(bot())
    i = interaction()
    await cog.settings.callback(cog, i)
    embed = i.response.send_message.await_args.kwargs["embed"]
    assert embed.title == "Embed Fixer"
    assert embed.description
    assert embed.image.url == "https://i.imgur.com/919Gum1.png"


@pytest.mark.parametrize("module", [info])
async def test_cog_setup_registers_expected_cog(module: Any) -> None:
    client = bot()
    await module.setup(client)
    assert client.add_cog.await_count == 1
    assert client.add_cog.await_args.args[0].bot is client
