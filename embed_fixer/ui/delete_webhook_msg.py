from typing import TYPE_CHECKING

from discord import ButtonStyle, Member, ui

from embed_fixer.bot import INTERACTION

from ..embed import DefaultEmbed
from .view import View

if TYPE_CHECKING:
    from ..bot import INTERACTION


class DeleteWebhookMsgView(View):
    async def start(self, *, sauces: list[str]) -> None:
        await super().start()

        fix_selector = DeleteMsgBtn()
        fix_selector.label = self.translate("delete")
        self.add_item(fix_selector)

        if sauces:
            sauce_btn = SauceBtn(sauces)
            sauce_btn.label = self.translate("sauce")
            self.add_item(sauce_btn)

    async def interaction_check(self, i: "INTERACTION") -> bool:
        if isinstance(i.user, Member):
            perms = i.user.guild_permissions
            if perms.manage_messages:
                check = True
        check = await super().interaction_check(i)

        if not check:
            await i.response.send_message(
                embed=DefaultEmbed(title=self.translate("delete_no_perms")), ephemeral=True
            )
        return check


class DeleteMsgBtn(ui.Button[DeleteWebhookMsgView]):
    def __init__(self) -> None:
        super().__init__(style=ButtonStyle.red)

    async def callback(self, i: "INTERACTION") -> None:
        if i.guild is None or self.view is None or i.message is None:
            return

        await i.response.defer()
        await i.message.delete()


class SauceBtn(ui.Button[DeleteWebhookMsgView]):
    def __init__(self, urls: list[str]) -> None:
        super().__init__()
        self.urls = urls

    async def callback(self, i: "INTERACTION") -> None:
        if self.view is None:
            return

        await i.response.send_message(
            embed=DefaultEmbed(
                title=self.view.translate("sauce"), description="\n".join(self.urls)
            ),
            ephemeral=True,
        )
