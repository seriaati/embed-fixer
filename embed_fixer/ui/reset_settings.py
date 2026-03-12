from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from embed_fixer.models import GuildFixMethod, GuildSettings
from embed_fixer.utils.embed import DefaultEmbed

from . import components as ui

if TYPE_CHECKING:
    from embed_fixer.bot import Interaction


class ResetSettingsView(ui.View):
    async def start(self, i: Interaction) -> None:
        embed = DefaultEmbed(title=self.translate("reset_confirm"))
        self.add_item(ConfirmButton(label=self.translate("reset_yes")))
        await i.response.send_message(embed=embed, view=self)


class ConfirmButton(ui.Button[ResetSettingsView]):
    def __init__(self, label: str) -> None:
        super().__init__(label=label, style=discord.ButtonStyle.red)

    async def callback(self, i: Interaction) -> None:
        if i.guild is None:
            return

        await GuildFixMethod.filter(guild_id=i.guild.id).delete()
        await GuildSettings.delete(id=i.guild.id)
        await i.response.edit_message(
            embed=DefaultEmbed(title=self.view.translate("reset_done")), view=None
        )
