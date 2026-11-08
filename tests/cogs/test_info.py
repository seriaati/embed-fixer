from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from embed_fixer.cogs import info
from embed_fixer.models import UserSettings
from tests.support.cogs import bot
from tests.support.ui import interaction

if TYPE_CHECKING:
    from typing import Any


@pytest.mark.usefixtures("db")
@pytest.mark.parametrize("lang", ["en_US", "es_ES", "nl", "vi", "zh_CN", "zh_TW"])
async def test_info_command_builds_translated_embed_image(lang: str) -> None:
    cog: Any = info.InfoCog(bot())
    i = interaction()
    settings, _ = await UserSettings.get_or_create(i.user.id)
    settings.lang = lang
    await settings.save()
    await cog.settings.callback(cog, i)
    embed = i.response.send_message.await_args.kwargs["embed"]
    assert embed.title == "Embed Fixer"
    assert embed.description
    assert "https://github.com/dededecline/embed-fixer)" in embed.description
    assert "https://github.com/dededecline/embed-fixer/issues)" in embed.description
    assert "https://github.com/dededecline/embed-fixer/blob/main/LICENSE)" in embed.description
    assert "seriaati" in embed.description
    assert "AGPL-3.0" in embed.description
    assert "discord://" not in embed.description
    assert "github.com/seriaati/embed-fixer" not in embed.description
    assert embed.image.url == "https://i.imgur.com/919Gum1.png"


@pytest.mark.parametrize("module", [info])
async def test_cog_setup_registers_expected_cog(module: Any) -> None:
    client = bot()
    await module.setup(client)
    assert client.add_cog.await_count == 1
    assert client.add_cog.await_args.args[0].bot is client
