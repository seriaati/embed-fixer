from __future__ import annotations

import pytest

from embed_fixer.fixes import DomainId
from embed_fixer.models import GuildFixMethod, GuildSettings
from embed_fixer.ui.reset_settings import ConfirmButton, ResetSettingsView
from tests.support.ui import interaction


@pytest.mark.usefixtures("db")
async def test_reset_requires_confirmation_and_only_deletes_selected_guild() -> None:
    selected = await GuildSettings.create(100)
    selected.bot_visibility = True
    await selected.save()
    await GuildSettings.create(101)
    await GuildFixMethod.create(guild_id=100, domain_id=DomainId.TWITTER, fix_id=1)
    await GuildFixMethod.create(guild_id=101, domain_id=DomainId.TWITTER, fix_id=1)
    view = ResetSettingsView(lang="en_US")
    i = interaction()
    await view.start(i)
    assert await GuildSettings.get_or_none(100) is not None
    assert i.response.send_message.await_args.kwargs["ephemeral"]
    button = view.children[0]
    assert isinstance(button, ConfirmButton)
    await button.callback(i)
    assert await GuildSettings.get_or_none(100) is None
    assert await GuildSettings.get_or_none(101) is not None
    assert await GuildFixMethod.filter(guild_id=100).count() == 0
    assert await GuildFixMethod.filter(guild_id=101).count() == 1
    assert i.response.edit_message.await_args.kwargs["view"] is None


@pytest.mark.usefixtures("db")
async def test_reset_confirmation_in_dm_does_nothing() -> None:
    button = ConfirmButton(label="Confirm")
    i = interaction(guild_id=None)
    await button.callback(i)
    i.response.edit_message.assert_not_awaited()
