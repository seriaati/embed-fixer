from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock, patch
from urllib.parse import parse_qs, urlparse

import discord
from tortoise import Tortoise

from embed_fixer.cogs import fixer
from embed_fixer.cogs.fixer import FixerCog, Media, MockMessage, PostExtractionResult
from embed_fixer.core.translator import translator
from embed_fixer.fixes import DOMAINS, DomainId
from embed_fixer.models import FixedMessage, GuildFixMethod, GuildSettings
from embed_fixer.settings import GuildSetting
from embed_fixer.ui.guild_settings import GuildSettingsView

if TYPE_CHECKING:
    from embed_fixer.ui import components as ui


class FixerTrackingTests(IsolatedAsyncioTestCase):
    cog: FixerCog

    async def asyncSetUp(self) -> None:
        await Tortoise.init(
            db_url="sqlite://:memory:", modules={"embed_fixer": ["embed_fixer.models"]}
        )
        await Tortoise.generate_schemas()
        await translator.load()
        self.cog = FixerCog(cast("Any", SimpleNamespace(session=None)))

    async def asyncTearDown(self) -> None:
        await Tortoise.close_connections()

    @staticmethod
    def message(content: str, *, guild: bool = False) -> MockMessage:
        return MockMessage(
            content=content,
            channel=cast("Any", SimpleNamespace(id=10)),
            guild=cast("Any", SimpleNamespace(id=20)) if guild else None,
            author=cast("Any", SimpleNamespace(id=30)),
        )

    async def test_fixed_and_original_links_keep_youtube_context(self) -> None:
        message = self.message(
            "https://www.youtube.com/watch?si=tracking&v=video&t=90&list=PL123&index=2#t=90"
        )
        result = await self.cog._find_fixes(message, settings=None, filesize_limit=1024)
        assert result.fix_found
        assert message.content == "https://koutube.com/watch?v=video&t=90&list=PL123&index=2#t=90"
        assert result.urls == ["https://www.youtube.com/watch?v=video&t=90&list=PL123&index=2#t=90"]
        kwargs: dict[str, Any] = {}
        self.cog._add_original_link_button(result.urls, True, "en_US", kwargs)
        button = cast("discord.ui.Button[Any]", kwargs["view"].children[0])
        assert button.url == result.urls[0]

    async def test_disabling_cleanup_preserves_tracking_and_functional_parameters(self) -> None:
        settings = GuildSettings.model_validate(
            {"id": 20, "strip_tracking_params": False, "enabled_domains": [DomainId.YOUTUBE]}
        )
        message = self.message("https://youtu.be/video?si=tracking&t=90", guild=True)
        result = await self.cog._find_fixes(message, settings=settings, filesize_limit=1024)
        assert message.content == "https://koutu.be/video?si=tracking&t=90"
        assert result.urls == ["https://youtu.be/video?si=tracking&t=90"]

    async def test_manual_fix_honors_persisted_server_preference(self) -> None:
        settings = GuildSettings.model_validate({"id": 20, "strip_tracking_params": False})
        await settings.save()
        message = self.message("https://youtu.be/video?si=tracking&t=90", guild=True)
        result = await self.cog._find_fixes(message, settings=None, filesize_limit=1024)
        assert result.fix_found
        assert message.content == "https://koutu.be/video?si=tracking&t=90"

    async def test_extraction_receives_cleaned_url_and_returns_cleaned_source(self) -> None:
        message = self.message("||https://www.instagram.com/p/ABC/?igsh=tracking&img_index=2||")
        extracted = PostExtractionResult(
            medias=[Media(url="https://media.example/image.jpg")], content="", author_md=""
        )
        with patch.object(
            self.cog, "_extract_post_info", new=AsyncMock(return_value=extracted)
        ) as extract:
            result = await self.cog._find_fixes(
                message, settings=None, filesize_limit=1024, extract_media=True
            )
        assert extract.await_args is not None
        assert extract.await_args.args[1] == "https://www.instagram.com/p/ABC/?img_index=2"
        assert result.sauces == ["https://www.instagram.com/p/ABC/?img_index=2"]
        assert result.urls == result.sauces
        assert not message.content

    async def test_disabled_extraction_cleanup_preserves_source_query(self) -> None:
        settings = GuildSettings.model_validate({"id": 20, "strip_tracking_params": False})
        message = self.message("https://www.instagram.com/p/ABC/?igsh=tracking&img_index=2")
        extracted = PostExtractionResult(
            medias=[Media(url="https://media.example/image.jpg")], content="", author_md=""
        )
        with patch.object(self.cog, "_extract_post_info", new=AsyncMock(return_value=extracted)):
            result = await self.cog._find_fixes(
                message, settings=settings, filesize_limit=1024, extract_media=True
            )
        assert result.sauces == ["https://www.instagram.com/p/ABC/?igsh=tracking&img_index=2"]

    async def test_unsupported_and_opted_out_links_are_untouched(self) -> None:
        original = (
            "https://example.com/?utm_source=test "
            "$https://youtu.be/ignored?si=tracking "
            "<https://youtu.be/ignored2?si=tracking> "
            "||https://youtu.be/video?si=tracking&t=2||"
        )
        message = self.message(original)
        result = await self.cog._find_fixes(message, settings=None, filesize_limit=1024)
        assert (
            message.content == "https://example.com/?utm_source=test "
            "$https://youtu.be/ignored?si=tracking "
            "<https://youtu.be/ignored2?si=tracking> "
            "||https://koutu.be/video?t=2||"
        )
        assert result.urls == ["https://youtu.be/video?t=2"]

    async def test_invalid_url_does_not_prevent_later_fix(self) -> None:
        message = self.message("https://[invalid/ https://youtu.be/video?si=tracking&t=2")
        result = await self.cog._find_fixes(message, settings=None, filesize_limit=1024)
        assert result.fix_found
        assert message.content == "https://[invalid/ https://koutu.be/video?t=2"

    async def test_each_url_is_cleaned_even_when_another_url_is_its_prefix(self) -> None:
        message = self.message("https://youtu.be/video https://youtu.be/video?si=tracking&t=90")
        result = await self.cog._find_fixes(message, settings=None, filesize_limit=1024)
        assert message.content == "https://koutu.be/video https://koutu.be/video?t=90"
        assert result.urls == ["https://youtu.be/video", "https://youtu.be/video?t=90"]

    async def test_matching_url_does_not_modify_opted_out_occurrences(self) -> None:
        message = self.message(
            "https://youtu.be/video?si=tracking "
            "<https://youtu.be/video?si=tracking> "
            "$https://youtu.be/video?si=tracking"
        )
        await self.cog._find_fixes(message, settings=None, filesize_limit=1024)
        assert message.content == (
            "https://koutu.be/video "
            "<https://youtu.be/video?si=tracking> "
            "$https://youtu.be/video?si=tracking"
        )

    async def test_nested_fix_preserves_query_and_round_trips(self) -> None:
        threads = next(domain for domain in DOMAINS if domain.id is DomainId.THREADS)
        fix = next(method for method in threads.fix_methods if method.id == 33)
        original = "https://threads.net/@user/post/ABC?foo=1&bar=two%2Fthree#section"
        fixed = fixer._apply_fix_to_url(original, fix, threads.id)
        assert fixed is not None
        assert parse_qs(urlparse(fixed).query) == {"url": [original]}
        reversed_url = fixer._reverse_parse_fixed_url(fixed)
        assert reversed_url is not None
        assert reversed_url[2] == original

    async def test_facebook_content_identifiers_survive(self) -> None:
        message = self.message(
            "https://www.facebook.com/story.php?story_fbid=123&id=456&mibextid=tracking"
        )
        result = await self.cog._find_fixes(message, settings=None, filesize_limit=1024)
        assert message.content == "https://facebed.seria.moe/story.php?story_fbid=123&id=456"
        assert result.urls == ["https://www.facebook.com/story.php?story_fbid=123&id=456"]

    async def test_nested_service_receives_cleaned_source_with_its_complete_query(self) -> None:
        settings, _ = await GuildSettings.get_or_create(id=20)
        await GuildFixMethod.create(guild_id=20, domain_id=DomainId.THREADS, fix_id=33)
        message = self.message("https://threads.net/@user/post/ABC?xmt=tracking&foo=1&bar=2#part")
        result = await self.cog._find_fixes(message, settings=settings, filesize_limit=1024)
        assert parse_qs(urlparse(message.content).query) == {
            "url": ["https://threads.net/@user/post/ABC?foo=1&bar=2#part"]
        }
        assert result.urls == ["https://threads.net/@user/post/ABC?foo=1&bar=2#part"]

    async def test_instagram_fetch_keeps_functional_query_parameters(self) -> None:
        with patch.object(
            self.cog.fetch_info, "instagram", new=AsyncMock(return_value=None)
        ) as fetch:
            await self.cog._extract_post_info(
                DomainId.INSTAGRAM, "https://instagram.com/p/ABC?img_index=2", filesize_limit=1024
            )
        assert fetch.await_args is not None
        assert fetch.await_args.args[0] == "https://instagram.com/p/ABC?img_index=2"

    async def test_rotation_cleans_urls_using_current_server_setting(self) -> None:
        for enabled, send_type in ((True, "resend"), (False, "resend"), (True, "webhook")):
            with self.subTest(enabled=enabled, send_type=send_type):
                settings, _ = await GuildSettings.get_or_create(id=20)
                settings.rotate_fix_reaction = True
                settings.strip_tracking_params = enabled
                await settings.save()
                await FixedMessage.update_or_create(
                    id=50,
                    defaults={
                        "guild_id": 20,
                        "channel_id": 10,
                        "author_id": 30,
                        "send_type": send_type,
                    },
                )
                message = Mock(spec=discord.Message)
                message.id = 50
                message.guild = SimpleNamespace(id=20)
                message.content = "https://fixupx.com/user/status/123?s=46&t=token&custom=1"
                message.edit = AsyncMock()
                original_link = "https://x.com/user/status/123?s=46&t=token&custom=1"
                view = discord.ui.View()
                view.add_item(discord.ui.Button(label="Original link", url=original_link))
                message.components = [
                    discord.ActionRow(cast("Any", data)) for data in view.to_components()
                ]
                channel = SimpleNamespace(fetch_message=AsyncMock(return_value=message))
                bot = cast("Any", self.cog.bot)
                bot.user = SimpleNamespace(id=40)
                bot.get_channel = Mock(return_value=channel)
                payload = SimpleNamespace(
                    guild_id=20, channel_id=10, message_id=50, user_id=30, emoji="🔄", member=None
                )
                webhook = SimpleNamespace(edit_message=AsyncMock())
                with patch.object(
                    self.cog, "_get_or_create_webhook", new=AsyncMock(return_value=webhook)
                ):
                    await self.cog.manage_rotate_fix_reaction(cast("Any", payload))
                edit = webhook.edit_message if send_type == "webhook" else message.edit
                assert edit.await_args is not None
                expected = "https://fixvx.com/user/status/123?"
                expected += "custom=1" if enabled else "s=46&t=token&custom=1"
                assert edit.await_args.kwargs["content"] == expected
                if enabled:
                    button = edit.await_args.kwargs["view"].children[0]
                    assert button.url == "https://x.com/user/status/123?custom=1"
                else:
                    assert "view" not in edit.await_args.kwargs

    async def test_server_toggle_persists_and_defaults_for_existing_records(self) -> None:
        settings, _ = await GuildSettings.get_or_create(id=20)
        assert settings.strip_tracking_params
        interaction = SimpleNamespace(
            guild_id=20,
            user=SimpleNamespace(id=30),
            response=SimpleNamespace(defer=AsyncMock()),
            followup=SimpleNamespace(send=AsyncMock()),
            original_response=AsyncMock(),
            edit_original_response=AsyncMock(),
        )
        guild = Mock(spec=discord.Guild)
        guild.id = 20
        guild.by_category.return_value = []
        guild.threads = []
        view = GuildSettingsView(guild=guild, lang="en_US", app_emojis={})
        await view.start(cast("Any", interaction), setting=GuildSetting.STRIP_TRACKING_PARAMS)
        container = cast("ui.Container", view.children[0])
        button = cast("discord.ui.Section[Any]", container.children[0]).accessory
        assert button is not None
        await button.callback(cast("Any", interaction))
        reloaded = await GuildSettings.get_or_none(id=20)
        assert reloaded is not None
        assert not reloaded.strip_tracking_params
