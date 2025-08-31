from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import aiofiles
import yaml
from discord import app_commands
from loguru import logger

from .models import GuildSettings

if TYPE_CHECKING:
    import discord

DEFAULT_LANG = "en_US"


class AppCommandTranslator(app_commands.Translator):
    def __init__(self, translator: Translator) -> None:
        super().__init__()
        self.translator = translator

    async def translate(
        self,
        string: app_commands.locale_str,
        locale: discord.Locale,
        _: discord.app_commands.TranslationContextTypes,
    ) -> str | None:
        if locale.value not in self.translator.langs:
            return None

        try:
            return self.translator.get(locale.value, string.message)
        except Exception:
            logger.exception("Failed to translate app command string")
            return None


class Translator:
    def __init__(self) -> None:
        self._l10n: dict[str, dict[str, str]] = {}
        self._l10n_names: dict[str, str] = {}

    @property
    def langs(self) -> dict[str, str]:
        return self._l10n_names

    @staticmethod
    async def get_guild_lang(guild: discord.Guild | None) -> str:
        lang = DEFAULT_LANG
        if guild is not None:
            guild_settings, _ = await GuildSettings.get_or_create(id=guild.id)
            lang = guild_settings.lang or guild.preferred_locale.value
        return lang

    async def load(self) -> None:
        # open all files in ./l10n/*.yaml
        for file in Path("./l10n").rglob("*.yaml"):
            async with aiofiles.open(file, encoding="utf-8") as f:
                data = yaml.safe_load(await f.read())
                self._l10n[file.stem] = data
                self._l10n_names[file.stem] = data["name"]

    def get(self, lang: str, key: str, **kwargs: Any) -> str:
        if lang not in self._l10n:
            lang = DEFAULT_LANG

        lang_map = self._l10n[lang]
        string = lang_map.get(key)
        if not string:
            if lang == DEFAULT_LANG:
                return key
            return self.get(DEFAULT_LANG, key, **kwargs)
        return string.format(**kwargs)
