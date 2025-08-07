from __future__ import annotations

from typing import TYPE_CHECKING, Final

import iso639
from discord import app_commands
from discord.app_commands import locale_str
from discord.ext import commands

from embed_fixer.fixes import DomainId
from embed_fixer.models import GuildFixMethod, GuildSettings
from embed_fixer.settings import Setting
from embed_fixer.translator import Translator
from embed_fixer.ui.guild_settings import DeleteMsgEmojiModal, GuildSettingsView

if TYPE_CHECKING:
    from embed_fixer.bot import EmbedFixer, Interaction

FIX_TO_DOMAIN_ID: Final[dict[str, DomainId]] = {
    "twitter.com": DomainId.TWITTER,
    "x.com": DomainId.TWITTER,
    "pixiv.net": DomainId.PIXIV,
    "tiktok.com": DomainId.TIKTOK,
    "reddit.com": DomainId.REDDIT,
    "instagram.com": DomainId.INSTAGRAM,
    "furaffinity.net": DomainId.FURAFFINITY,
    "clips.twitch.tv": DomainId.TWITCH_CLIPS,
    "m.twitch.tv": DomainId.TWITCH_CLIPS,
    "twitch.tv": DomainId.TWITCH_CLIPS,
    "iwara.tv": DomainId.IWARA,
    "bsky.app": DomainId.BLUESKY,
    "kemono.su": DomainId.KEMONO,
    "facebook.com": DomainId.FACEBOOK,
    "b23.tv": DomainId.BILIBILI,
    "m.bilibili.com": DomainId.BILIBILI,
    "bilibili.com": DomainId.BILIBILI,
    "tumblr.com": DomainId.TUMBLR,
    "threads.net": DomainId.THREADS,
}
ISO639_LANGS = {lang.pt1: lang.name for lang in iso639.iter_langs() if lang.pt1}


class SettingsCog(commands.Cog):
    def __init__(self, bot: EmbedFixer) -> None:
        self.bot = bot

    @staticmethod
    async def _db_migration(guild_id: int) -> None:
        settings = await GuildSettings.get_or_none(id=guild_id)
        if settings is None:
            return

        for fix in settings.disabled_fixes:
            domain_id = FIX_TO_DOMAIN_ID.get(fix)
            if domain_id is None:
                continue

            settings.disabled_domains.append(domain_id.value)

        if settings.use_vxreddit:
            vxreddit_fix = await GuildFixMethod.get_or_none(
                guild_id=guild_id, domain_id=DomainId.REDDIT, fix_id=7
            )
            if vxreddit_fix is None:
                await GuildFixMethod.create(guild_id=guild_id, domain_id=DomainId.REDDIT, fix_id=7)

        settings.disabled_domains = list(set(settings.disabled_domains))
        settings.disabled_fixes = []
        settings.use_vxreddit = False
        await settings.save(update_fields=("disabled_fixes", "disabled_domains", "use_vxreddit"))

    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.guild_only()
    @app_commands.default_permissions()
    @app_commands.choices(
        setting=[
            app_commands.Choice(name=locale_str(setting), value=setting) for setting in Setting
        ]
    )
    @app_commands.rename(setting=locale_str("setting_param"))
    @app_commands.describe(setting=locale_str("setting_param_desc"))
    @app_commands.command(name="settings", description=locale_str("settings_cmd_desc"))
    async def settings(self, i: Interaction, setting: Setting) -> None:
        if i.guild is None:
            return

        await self._db_migration(i.guild.id)

        if setting is Setting.DELETE_MSG_EMOJI:
            settings, _ = await GuildSettings.get_or_create(id=i.guild.id)
            await i.response.send_modal(
                DeleteMsgEmojiModal(i.guild, self.bot.translator, settings=settings)
            )
            return

        view = GuildSettingsView(i.guild, self.bot.translator)
        await view.start(i, setting=setting)

    @commands.is_owner()
    @commands.guild_only()
    @commands.command(name="gs")
    async def get_guild_settings(self, ctx: commands.Context) -> None:
        if ctx.guild is None:
            return

        settings, _ = await GuildSettings.get_or_create(id=ctx.guild.id)
        await ctx.send(str(settings))

    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.guild_only()
    @app_commands.default_permissions()
    @app_commands.rename(translang=locale_str("translang_param"))
    @app_commands.describe(translang=locale_str("translang_param_desc"))
    @app_commands.command(name="translang", description=locale_str("translang_cmd_desc"))
    async def translang_command(self, i: Interaction, translang: str) -> None:
        if i.guild is None:
            return

        if translang.lower() == "disable":
            await i.response.defer(ephemeral=True)

            settings, _ = await GuildSettings.get_or_create(id=i.guild.id)
            settings.translate_target_lang = None
            await settings.save(update_fields=("translate_target_lang",))

            await i.followup.send(
                self.bot.translator.get(
                    await Translator.get_guild_lang(i.guild), "translang_disabled"
                ),
                ephemeral=True,
            )
            return

        if translang not in ISO639_LANGS:
            await i.response.send_message(
                self.bot.translator.get(
                    await Translator.get_guild_lang(i.guild), "invalid_translang"
                ),
                ephemeral=True,
            )
            return

        await i.response.defer(ephemeral=True)

        settings, _ = await GuildSettings.get_or_create(id=i.guild.id)
        settings.translate_target_lang = translang
        await settings.save(update_fields=("translate_target_lang",))

        await i.followup.send(
            self.bot.translator.get(
                await Translator.get_guild_lang(i.guild),
                "translang_set",
                lang_name=ISO639_LANGS.get(translang, translang),
            ),
            ephemeral=True,
        )

    @translang_command.autocomplete("translang")
    async def translang_autocomplete(
        self, _: Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        choices = [
            app_commands.Choice(name="Disable", value="disable"),
            *[app_commands.Choice(name=name, value=code) for code, name in ISO639_LANGS.items()],
        ]
        return [
            c
            for c in choices
            if current.lower() in c.name.lower() or current.lower() in c.value.lower()
        ][:25]


async def setup(bot: EmbedFixer) -> None:
    await bot.add_cog(SettingsCog(bot))
