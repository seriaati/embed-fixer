from __future__ import annotations

import pytest

from embed_fixer.fixes import (
    DOMAINS,
    EXTRACTABLE_DOMAIN_IDS,
    AppendURLFix,
    Domain,
    DomainId,
    FixMethod,
    ReplaceFix,
    Website,
)

URL_CASES = [
    (DomainId.TWITTER, "https://twitter.com/alice/status/123"),
    (DomainId.TWITTER, "https://x.com/alice/status/123/video/1"),
    (DomainId.PIXIV, "https://www.pixiv.net/en/artworks/123"),
    (DomainId.TIKTOK, "https://www.tiktok.com/@alice.abc/video/123"),
    (DomainId.TIKTOK, "https://www.tiktok.com/@alice/photo/123"),
    (DomainId.TIKTOK, "https://www.tiktok.com/t/abc"),
    (DomainId.TIKTOK, "https://vm.tiktok.com/abc"),
    (DomainId.TIKTOK, "https://vt.tiktok.com/abc"),
    (DomainId.REDDIT, "https://old.reddit.com/r/cats/comments/abc/title"),
    (DomainId.REDDIT, "https://www.reddit.com/r/cats/s/abc"),
    (DomainId.REDDIT, "https://reddit.com/user/alice/comments/abc/title"),
    (DomainId.INSTAGRAM, "https://www.instagram.com/share/abc"),
    (DomainId.INSTAGRAM, "https://instagram.com/p/abc"),
    (DomainId.INSTAGRAM, "https://instagram.com/reel/abc"),
    (DomainId.INSTAGRAM, "https://instagram.com/share/reels/abc"),
    (DomainId.INSTAGRAM, "https://instagram.com/stories/alice.abc/123"),
    (DomainId.FURAFFINITY, "https://www.furaffinity.net/view/123"),
    (DomainId.TWITCH_CLIPS, "https://m.twitch.tv/clip/abc"),
    (DomainId.TWITCH_CLIPS, "https://clips.twitch.tv/abc"),
    (DomainId.TWITCH_CLIPS, "https://www.twitch.tv/alice/clip/abc"),
    (DomainId.IWARA, "https://www.iwara.tv/video/abc/title"),
    (DomainId.BLUESKY, "https://bsky.app/profile/alice.bsky.social/post/abc"),
    (DomainId.KEMONO, "https://kemono.su/patreon/user/123/post/456"),
    (DomainId.FACEBOOK, "https://www.facebook.com/share/r/abc"),
    (DomainId.FACEBOOK, "https://web.facebook.com/reel/123"),
    (DomainId.FACEBOOK, "https://facebook.com/share/v/abc"),
    (DomainId.FACEBOOK, "https://facebook.com/marketplace/item/123"),
    (DomainId.FACEBOOK, "https://facebook.com/alice/posts/123"),
    (DomainId.BILIBILI, "https://m.bilibili.com/video/BV123"),
    (DomainId.BILIBILI, "https://b23.tv/abc"),
    (DomainId.BILIBILI_OPUS, "https://bilibili.com/opus/123"),
    (DomainId.BILIBILI_OPUS, "https://t.bilibili.com/123"),
    (DomainId.TUMBLR, "https://www.tumblr.com/alice/123/title"),
    (DomainId.THREADS, "https://www.threads.net/@alice.abc"),
    (DomainId.THREADS, "https://threads.com/@alice/post/abc"),
    (DomainId.THREADS, "https://threads.net/share/abc"),
    (DomainId.PTT, "https://www.ptt.cc/bbs/Gossiping/M.123.A.ABC.html"),
    (DomainId.DEVIANTART, "https://www.deviantart.com/alice/art/Title-123"),
    (DomainId.PINTEREST, "https://www.pinterest.com/pin/123"),
    (DomainId.YOUTUBE, "https://www.youtube.com/watch?v=abc-123"),
    (DomainId.YOUTUBE, "https://youtu.be/abc-123"),
]


@pytest.mark.parametrize(("domain_id", "url"), URL_CASES)
def test_registry_recognizes_supported_platform_urls(domain_id: DomainId, url: str) -> None:
    matches = [domain.id for domain in DOMAINS if any(site.match(url) for site in domain.websites)]
    assert matches == [domain_id]


def test_every_registered_website_has_a_representative_url() -> None:
    for domain in DOMAINS:
        examples = [url for domain_id, url in URL_CASES if domain_id == domain.id]
        assert all(any(site.match(url) for url in examples) for site in domain.websites)


def test_registry_ids_defaults_and_references_are_consistent() -> None:
    assert {domain.id for domain in DOMAINS} == set(DomainId)
    assert len(DOMAINS) == len(DomainId)
    method_ids = [method.id for domain in DOMAINS for method in domain.fix_methods]
    assert len(method_ids) == len(set(method_ids))
    assert set(EXTRACTABLE_DOMAIN_IDS) <= {domain.id for domain in DOMAINS}
    for domain in DOMAINS:
        assert domain.websites
        assert sum(method.default for method in domain.fix_methods) <= 1
        for website in domain.websites:
            assert set(website.skip_method_ids or []) <= {
                method.id for method in domain.fix_methods
            }
        for method in domain.fix_methods:
            assert domain.get_fix_method(method.id) is method
            assert method.fixes
            for fix in method.fixes:
                if isinstance(fix, ReplaceFix):
                    assert fix.old_domain
                    assert fix.new_domain
                else:
                    assert isinstance(fix, AppendURLFix)
                    assert fix.domain
        assert domain.get_fix_method(-1) is None
    assert [domain.id for domain in DOMAINS if not domain.enabled_by_default] == [DomainId.YOUTUBE]


@pytest.mark.parametrize(
    ("domain_id", "fix_id"),
    [
        (DomainId.TWITTER, 1),
        (DomainId.INSTAGRAM, 37),
        (DomainId.FACEBOOK, 25),
        (DomainId.PTT, 24),
        (DomainId.PINTEREST, 38),
        (DomainId.KEMONO, None),
        (DomainId.YOUTUBE, 39),
    ],
)
def test_platform_default_services(domain_id: DomainId, fix_id: int | None) -> None:
    domain = next(domain for domain in DOMAINS if domain.id == domain_id)
    method = domain.default_fix_method
    assert (method.id if method is not None else None) == fix_id


def test_default_fix_prefers_explicit_default_then_first_and_handles_empty() -> None:
    first = FixMethod(id=1, name="first", fixes=[])
    preferred = FixMethod(id=2, name="preferred", fixes=[], default=True)
    domain = Domain(
        id=DomainId.TWITTER, name="Example", websites=[], fix_methods=[first, preferred]
    )
    assert domain.default_fix_method is preferred
    preferred.default = False
    assert domain.default_fix_method is first
    domain.fix_methods.clear()
    assert domain.default_fix_method is None


def test_website_requires_https_and_matching_resource_shape() -> None:
    website = Website(r"https://example\.com/posts/\d+")
    assert website.match("https://example.com/posts/123?tracking=1")
    assert not website.match("http://example.com/posts/123")
    assert not website.match("https://example.com/posts/abc")
    assert not website.match("prefix https://example.com/posts/123")


@pytest.mark.parametrize(
    ("domain_id", "stored_id", "fix_ids", "default_fix_id"),
    [
        (DomainId.TWITTER, 1, [1, 2, 29], 1),
        (DomainId.PIXIV, 2, [3], 3),
        (DomainId.TIKTOK, 3, [4, 27, 31], 4),
        (DomainId.REDDIT, 4, [6, 7, 26], 6),
        (DomainId.INSTAGRAM, 5, [8, 9, 23, 34, 35, 37], 37),
        (DomainId.FURAFFINITY, 6, [10, 28], 10),
        (DomainId.TWITCH_CLIPS, 7, [11], 11),
        (DomainId.IWARA, 8, [12], 12),
        (DomainId.BLUESKY, 9, [13, 14], 13),
        (DomainId.KEMONO, 10, [], None),
        (DomainId.FACEBOOK, 11, [15, 16, 25], 25),
        (DomainId.BILIBILI, 12, [17, 18, 22], 17),
        (DomainId.TUMBLR, 13, [19], 19),
        (DomainId.THREADS, 14, [20, 21, 33], 20),
        (DomainId.PTT, 15, [24], 24),
        (DomainId.DEVIANTART, 16, [32], 32),
        (DomainId.BILIBILI_OPUS, 17, [36], 36),
        (DomainId.PINTEREST, 18, [38], 38),
        (DomainId.YOUTUBE, 19, [39], 39),
    ],
)
def test_persisted_domain_and_fix_identifiers_remain_stable(
    domain_id: DomainId, stored_id: int, fix_ids: list[int], default_fix_id: int | None
) -> None:
    domain = next(domain for domain in DOMAINS if domain.id == domain_id)
    assert domain_id.value == stored_id
    assert [method.id for method in domain.fix_methods] == fix_ids
    method = domain.default_fix_method
    assert (method.id if method else None) == default_fix_id
