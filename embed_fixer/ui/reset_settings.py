from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from embed_fixer.embed import DefaultEmbed
from embed_fixer.models import GuildSettings
from embed_fixer.ui.components import View

if TYPE_CHECKING:
    from embed_fixer.bot import Interaction


class ResetSettingsView(View):
    async def start(self, i: Interaction) -> None:
        await super().start()
        embed = DefaultEmbed(title=self.translate("reset_confirm"))
        self.add_item(ConfirmButton(label=self.translate("reset_yes")))
        await i.response.send_message(embed=embed, view=self)


class ConfirmButton(discord.ui.Button[ResetSettingsView]):
    def __init__(self, label: str) -> None:
        super().__init__(label=label, style=discord.ButtonStyle.red)

    async def callback(self, i: Interaction) -> None:
        if self.view is None:
            return

        await GuildSettings.filter(id=self.view.guild.id).delete()
        await i.response.edit_message(
            embed=DefaultEmbed(title=self.view.translate("reset_done")), view=None
        )
