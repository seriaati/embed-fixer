from __future__ import annotations

import importlib
from typing import TYPE_CHECKING
from unittest.mock import Mock

import discord
import pytest
from discord import app_commands

from embed_fixer.core.translator import DEFAULT_LANG, AppCommandTranslator, Translator, translator
from embed_fixer.models import GuildSettings, UserSettings

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("lang", "expected"),
    [
        ("en_US", "Hello Ada"),
        ("en-US", "Hello Ada"),
        ("fr", "Salut Ada"),
        ("es-419", "Hola Ada"),
        ("unsupported", "Hello Ada"),
    ],
)
def test_language_normalization_and_template_formatting(lang: str, expected: str) -> None:
    local = Translator()
    local._l10n = {
        "en_US": {"hello": "Hello {name}"},
        "fr": {"hello": "Salut {name}"},
        "es_ES": {"hello": "Hola {name}"},
    }
    assert local.translate("hello", lang=lang, name="Ada") == expected


def test_missing_and_empty_translations_fall_back_to_english_then_key() -> None:
    local = Translator()
    local._l10n = {
        "en_US": {"only_english": "Welcome {name}", "empty": "English"},
        "fr": {"empty": ""},
    }
    assert local.translate("only_english", lang="fr", name="Ada") == "Welcome Ada"
    assert local.translate("empty", lang="fr") == "English"
    assert local.translate("missing", lang="fr") == "missing"
    assert local.translate("missing", lang="en_US") == "missing"
    with pytest.raises(KeyError, match="name"):
        local.translate("only_english", lang="fr")


async def test_load_reads_nested_yaml_and_exposes_display_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    locale_dir = tmp_path / "l10n"
    (locale_dir / "nested").mkdir(parents=True)
    (locale_dir / "en_US.yaml").write_text("name: English\ngreeting: Hello {name}\n")
    (locale_dir / "nested" / "fr.yaml").write_text("name: Français\ngreeting: Bonjour {name}\n")
    (locale_dir / "ignored.txt").write_text("not YAML")
    monkeypatch.chdir(tmp_path)
    local = Translator()
    assert local.langs == {}
    await local.load()
    assert local.langs == {"en_US": "English", "fr": "Français"}
    assert local.translate("greeting", lang="fr", name="Ada") == "Bonjour Ada"


def test_real_locale_files_load_with_default_and_language_names() -> None:
    assert DEFAULT_LANG in translator.langs
    assert set(translator.langs) == {"en_US", "nl", "es_ES", "zh_CN", "zh_TW", "vi"}
    assert all(name for name in translator.langs.values())
    for lang in translator.langs:
        assert translator.translate("name", lang=lang) == translator.langs[lang]
    assert translator.translate("unknown.test.key", lang="unknown") == "unknown.test.key"


@pytest.mark.usefixtures("db")
async def test_guild_language_prefers_settings_then_discord_locale() -> None:
    guild = Mock(spec=discord.Guild, id=1, preferred_locale=discord.Locale.japanese)
    assert await translator.get_guild_lang(None) == DEFAULT_LANG
    assert await translator.get_guild_lang(guild) == "ja"
    settings = await GuildSettings.get_or_none(1)
    assert settings is not None
    settings.lang = "fr"
    await settings.save()
    assert await translator.get_guild_lang(guild) == "fr"


@pytest.mark.usefixtures("db")
async def test_user_language_defaults_and_persists_override() -> None:
    assert await translator.get_user_lang(1) == DEFAULT_LANG
    settings = await UserSettings.get_or_none(1)
    assert settings is not None
    settings.lang = "zh_TW"
    await settings.save()
    assert await translator.get_user_lang(1) == "zh_TW"


async def test_app_command_translator_uses_discord_locale() -> None:
    result = await AppCommandTranslator().translate(
        app_commands.locale_str("name"),
        discord.Locale.american_english,
        Mock(spec=app_commands.TranslationContext),
    )
    assert result == translator.langs[DEFAULT_LANG]


async def test_app_command_translation_errors_retry_in_default_language(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = importlib.import_module("embed_fixer.core.translator")
    translate = Mock(side_effect=[ValueError("invalid locale"), "Fallback"])
    monkeypatch.setattr(module.translator, "translate", translate)
    result = await AppCommandTranslator().translate(
        app_commands.locale_str("hello"),
        discord.Locale.french,
        Mock(spec=app_commands.TranslationContext),
    )
    assert result == "Fallback"
    assert translate.call_args_list[0].kwargs == {"lang": "fr"}
    assert translate.call_args_list[1].kwargs == {"lang": DEFAULT_LANG}
