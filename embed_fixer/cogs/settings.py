from __future__ import annotations

import io
import json
from typing import TYPE_CHECKING, Final

import discord
import iso639
from discord import app_commands
from discord.app_commands import locale_str
from discord.ext import commands

from embed_fixer.core.translator import Translator, translator
from embed_fixer.fixes import DomainId
from embed_fixer.models import GuildFixMethod, GuildSettings, IgnoreMe, UserSettings
from embed_fixer.settings import GuildSetting
from embed_fixer.ui.guild_settings import (
    DeleteMsgEmojiModal,
    GuildSettingsView,
    RemoveDeleteReactionAfterModal,
)
from embed_fixer.ui.reset_settings import ResetSettingsView
from embed_fixer.ui.user_settings import UserSettingsView

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
            app_commands.Choice(name=locale_str(setting), value=setting) for setting in GuildSetting
        ]
    )
    @app_commands.rename(setting=locale_str("setting_param"))
    @app_commands.describe(setting=locale_str("setting_param_desc"))
    @app_commands.command(name="settings", description=locale_str("settings_cmd_desc"))
    async def settings(self, i: Interaction, setting: GuildSetting) -> None:
        if i.guild is None:
            return

        await self._db_migration(i.guild.id)
        settings, _ = await GuildSettings.get_or_create(id=i.guild.id)

        if setting is GuildSetting.DELETE_MSG_EMOJI:
            await i.response.send_modal(DeleteMsgEmojiModal(settings=settings))
            return

        if setting is GuildSetting.REMOVE_DELETE_REACTION_AFTER:
            await i.response.send_modal(RemoveDeleteReactionAfterModal(settings=settings))
            return

        view = GuildSettingsView(guild=i.guild, lang=settings.lang, app_emojis=self.bot.app_emojis)
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

        lang = await Translator.get_guild_lang(i.guild)

        if translang.lower() == "disable":
            await i.response.defer(ephemeral=True)

            settings, _ = await GuildSettings.get_or_create(id=i.guild.id)
            settings.translate_target_lang = None
            await settings.save(update_fields=("translate_target_lang",))

            await i.followup.send(
                translator.translate("translang_disabled", lang=lang), ephemeral=True
            )
            return

        if translang not in ISO639_LANGS:
            await i.response.send_message(
                translator.translate("invalid_translang", lang=lang), ephemeral=True
            )
            return

        await i.response.defer(ephemeral=True)

        settings, _ = await GuildSettings.get_or_create(id=i.guild.id)
        settings.translate_target_lang = translang
        await settings.save(update_fields=("translate_target_lang",))

        await i.followup.send(
            translator.translate(
                "translang_set", lang=lang, lang_name=ISO639_LANGS.get(translang, translang)
            ),
            ephemeral=True,
        )

    @translang_command.autocomplete("translang")
    async def translang_autocomplete(
        self, _: Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        choices = [
            app_commands.Choice(name=locale_str("translang_disable"), value="disable"),
            *[app_commands.Choice(name=name, value=code) for code, name in ISO639_LANGS.items()],
        ]
        return [
            c
            for c in choices
            if current.lower() in c.name.lower() or current.lower() in c.value.lower()
        ][:25]

    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.guild_only()
    @app_commands.default_permissions()
    @app_commands.command(name="reset", description=locale_str("reset_cmd_desc"))
    async def reset_settings_command(self, i: Interaction) -> None:
        if i.guild is None:
            return

        lang = await Translator.get_guild_lang(i.guild)
        view = ResetSettingsView(lang=lang)
        await view.start(i)

    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.guild_only()
    @app_commands.default_permissions()
    @app_commands.command(name="export", description=locale_str("export_cmd_desc"))
    async def export_settings_command(self, i: Interaction) -> None:
        if i.guild is None:
            return

        await i.response.defer(ephemeral=True)

        settings, _ = await GuildSettings.get_or_create(id=i.guild.id)
        fix_methods = await GuildFixMethod.filter(guild_id=i.guild.id)
        data = {
            "guild_settings": settings.model_dump(exclude={"id"}),
            "fix_methods": [
                {"domain_id": fm.domain_id.value, "fix_id": fm.fix_id} for fm in fix_methods
            ],
        }

        lang = await Translator.get_guild_lang(i.guild)
        file_ = discord.File(
            io.BytesIO(json.dumps(data, indent=2).encode()),
            filename=f"embed_fixer_settings_{i.guild.id}.json",
        )
        await i.followup.send(
            translator.translate("export_done", lang=lang), file=file_, ephemeral=True
        )

    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.guild_only()
    @app_commands.default_permissions()
    @app_commands.rename(file=locale_str("import_file_param"))
    @app_commands.describe(file=locale_str("import_file_param_desc"))
    @app_commands.command(name="import", description=locale_str("import_cmd_desc"))
    async def import_settings_command(self, i: Interaction, file: discord.Attachment) -> None:
        if i.guild is None:
            return

        await i.response.defer(ephemeral=True)
        lang = await Translator.get_guild_lang(i.guild)

        if file.size > 1024 * 1024:
            await i.followup.send(
                translator.translate("import_invalid_file", lang=lang), ephemeral=True
            )
            return

        try:
            data = json.loads(await file.read())
            settings = GuildSettings(id=i.guild.id, **data["guild_settings"])
            fix_methods = {
                (DomainId(fm["domain_id"]), int(fm["fix_id"])) for fm in data.get("fix_methods", [])
            }
        except (ValueError, TypeError, KeyError):
            await i.followup.send(
                translator.translate("import_invalid_file", lang=lang), ephemeral=True
            )
            return

        await settings.save()
        await GuildFixMethod.filter(guild_id=i.guild.id).delete()
        for domain_id, fix_id in fix_methods:
            await GuildFixMethod.create(guild_id=i.guild.id, domain_id=domain_id, fix_id=fix_id)

        await i.followup.send(translator.translate("import_done", lang=lang), ephemeral=True)

    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.command(name="ignore-me", description=locale_str("ignore_me_cmd_desc"))
    async def ignore_me_command(self, i: Interaction) -> None:
        await i.response.defer(ephemeral=True)

        lang = await Translator.get_user_lang(i.user.id)

        toggled = await IgnoreMe.toggle(i.user.id)
        if toggled:
            await i.followup.send(
                translator.translate("ignore_me_enabled", lang=lang), ephemeral=True
            )
        else:
            await i.followup.send(
                translator.translate("ignore_me_disabled", lang=lang), ephemeral=True
            )

    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.command(name="user-settings", description=locale_str("user_settings_cmd_desc"))
    async def user_settings_command(self, i: Interaction) -> None:
        await i.response.defer(ephemeral=True)

        settings, _ = await UserSettings.get_or_create(id=i.user.id)
        view = UserSettingsView(
            app_emojis=self.bot.app_emojis,
            settings=settings,
            lang=await Translator.get_user_lang(i.user.id),
        )
        await i.followup.send(view=view, ephemeral=True)


async def setup(bot: EmbedFixer) -> None:
    await bot.add_cog(SettingsCog(bot))
