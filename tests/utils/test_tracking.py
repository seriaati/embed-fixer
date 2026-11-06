from __future__ import annotations

import pytest

from embed_fixer.utils.tracking import remove_tracking_params


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://x.com/user/status/123?s=46&t=token", "https://x.com/user/status/123"),
        (
            "https://twitter.com/user/status/123/video/1?ref_src=embed&ref_url=site",
            "https://twitter.com/user/status/123/video/1",
        ),
        (
            "https://www.pixiv.net/en/artworks/123?from=share&p=2",
            "https://www.pixiv.net/en/artworks/123?p=2",
        ),
        (
            "https://www.tiktok.com/@user/video/123?_t=abc&_r=1&is_from_webapp=1&sender_device=pc",
            "https://www.tiktok.com/@user/video/123",
        ),
        (
            "https://www.tiktok.com/@user/photo/123?sec_user_id=sharer&share_link_id=id&timestamp=123&photo_id=2",
            "https://www.tiktok.com/@user/photo/123?photo_id=2",
        ),
        ("https://vm.tiktok.com/ABC/?u_code=id&share_iid=123", "https://vm.tiktok.com/ABC/"),
        ("https://vt.tiktok.com/ABC/?share_app_id=123&tt_from=copy", "https://vt.tiktok.com/ABC/"),
        (
            "https://www.tiktok.com/t/ABC/?trackParams=x&ug_btm=1&source=h5",
            "https://www.tiktok.com/t/ABC/",
        ),
        (
            "https://old.reddit.com/r/test/comments/abc/title/comment/?share_id=123&context=3&sort=top",
            "https://old.reddit.com/r/test/comments/abc/title/comment/?context=3&sort=top",
        ),
        (
            "https://www.reddit.com/r/test/s/ABC?utm_source=share&_branch_match_id=1",
            "https://www.reddit.com/r/test/s/ABC",
        ),
        (
            "https://www.instagram.com/p/ABC/?igsh=abc&img_index=2",
            "https://www.instagram.com/p/ABC/?img_index=2",
        ),
        (
            "https://www.instagram.com/reel/ABC/?igshid=123&ig_rid=456&stkn=789",
            "https://www.instagram.com/reel/ABC/",
        ),
        (
            "https://www.instagram.com/stories/user/123?igsh=abc",
            "https://www.instagram.com/stories/user/123",
        ),
        (
            "https://www.instagram.com/share/reel/ABC/?igsh=abc",
            "https://www.instagram.com/share/reel/ABC/",
        ),
        (
            "https://clips.twitch.tv/Clip?tt_medium=mobile&tt_content=clip&t=2",
            "https://clips.twitch.tv/Clip?t=2",
        ),
        (
            "https://www.twitch.tv/user/clip/Clip?tt_medium=mobile&tt_content=clip",
            "https://www.twitch.tv/user/clip/Clip",
        ),
        (
            "https://bsky.app/profile/user.bsky.social/post/abc?ref_src=embed",
            "https://bsky.app/profile/user.bsky.social/post/abc",
        ),
        (
            "https://www.facebook.com/photo.php?fbid=123&set=abc&type=3&mibextid=tracking&fbclid=click",
            "https://www.facebook.com/photo.php?fbid=123&set=abc&type=3",
        ),
        (
            "https://www.facebook.com/watch/?v=123&rdid=token",
            "https://www.facebook.com/watch/?v=123",
        ),
        (
            "https://web.facebook.com/share/r/ABC/?mibextid=token",
            "https://web.facebook.com/share/r/ABC/",
        ),
        (
            "https://www.facebook.com/marketplace/item/123?tracking=token&ref=share",
            "https://www.facebook.com/marketplace/item/123",
        ),
        (
            "https://www.bilibili.com/video/BV123?p=2&t=90&spm_id_from=333&vd_source=abc",
            "https://www.bilibili.com/video/BV123?p=2&t=90",
        ),
        (
            "https://m.bilibili.com/opus/123?share_source=copy&timestamp=123",
            "https://m.bilibili.com/opus/123",
        ),
        (
            "https://t.bilibili.com/123?share_medium=android&share_tag=web",
            "https://t.bilibili.com/123",
        ),
        ("https://b23.tv/ABC?share_source=copy&share_session_id=123", "https://b23.tv/ABC"),
        (
            "https://www.tumblr.com/user/123/title?source=share",
            "https://www.tumblr.com/user/123/title",
        ),
        (
            "https://www.threads.net/@user/post/ABC?xmt=token&igshid=token",
            "https://www.threads.net/@user/post/ABC",
        ),
        (
            "https://www.threads.com/@user/post/ABC?xmt=token&slof=1",
            "https://www.threads.com/@user/post/ABC?slof=1",
        ),
        ("https://youtu.be/video?si=token&t=1m30s", "https://youtu.be/video?t=1m30s"),
        (
            "https://www.youtube.com/watch?v=video&feature=shared&pp=tracking&start=90&end=120&list=PL1&index=2&lc=comment",
            "https://www.youtube.com/watch?v=video&start=90&end=120&list=PL1&index=2&lc=comment",
        ),
    ],
)
def test_platform_tracking_parameters(url: str, expected: str) -> None:
    assert remove_tracking_params(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "https://www.furaffinity.net/view/123/",
        "https://www.iwara.tv/video/abc/title",
        "https://kemono.su/patreon/user/123/post/456",
        "https://www.ptt.cc/bbs/Test/M.123.A.ABC.html",
        "https://www.deviantart.com/user/art/title-123",
        "https://www.pinterest.com/pin/123/",
    ],
)
def test_global_trackers_on_other_supported_platforms(url: str) -> None:
    assert (
        remove_tracking_params(f"{url}?utm_source=share&fbclid=click&custom=1") == f"{url}?custom=1"
    )


def test_unknown_parameters_and_encoding_survive_exactly() -> None:
    url = "https://youtu.be/video?si=tracking&t=1m30s&token=a%2fb%2B%20c+z&flag&empty=&x=1&x=2#t=90&si=keep"
    assert (
        remove_tracking_params(url)
        == "https://youtu.be/video?t=1m30s&token=a%2fb%2B%20c+z&flag&empty=&x=1&x=2#t=90&si=keep"
    )


def test_encoded_tracking_names_and_duplicate_trackers_are_removed() -> None:
    assert (
        remove_tracking_params("https://youtu.be/video?%73i=a&si=b&%75tm_source=x&t=3")
        == "https://youtu.be/video?t=3"
    )


@pytest.mark.parametrize(
    "url",
    [
        "https://youtu.be/video",
        "https://youtu.be/video?",
        "https://youtu.be/video?x=%2f+%20&flag&empty=&x=2#",
        "https://example.com/?s=1&t=2&si=3&from=4&source=5&ref=6",
        "https://youtube.com.example/watch?v=video&si=tracking",
    ],
)
def test_unmodified_urls_are_byte_for_byte_identical(url: str) -> None:
    assert remove_tracking_params(url) == url


def test_cleanup_is_idempotent() -> None:
    url = "https://youtu.be/video?si=tracking&t=3&empty=#section"
    cleaned = remove_tracking_params(url)
    assert remove_tracking_params(cleaned) == cleaned


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("/relative?utm_source=share&a=1", "/relative?a=1"),
        (
            "https://X.COM:443/u/status/1?S=1&T=2&UTM_Source=s&safe=1#",
            "https://X.COM:443/u/status/1?safe=1#",
        ),
        (
            "https://example.org/path?mtm_campaign=share&_ga=1&mc_cid=2&keep=",
            "https://example.org/path?keep=",
        ),
        ("https://example.org/path?utm_source=x#?keep=1", "https://example.org/path#?keep=1"),
    ],
)
def test_global_names_case_and_relative_urls(url: str, expected: str) -> None:
    assert remove_tracking_params(url) == expected
