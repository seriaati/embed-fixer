from __future__ import annotations

from typing import Final
from urllib.parse import unquote_plus, urlsplit

GLOBAL_TRACKING_PARAMS: Final = frozenset(
    {"fbclid", "gclid", "dclid", "msclkid", "twclid", "ttclid", "_ga", "_gl", "mc_cid", "mc_eid"}
)
GLOBAL_TRACKING_PREFIXES: Final = ("utm_", "mtm_")

TWITTER_TRACKING_PARAMS: Final = frozenset({"s", "t", "src", "ref_src", "ref_url", "cn"})
YOUTUBE_TRACKING_PARAMS: Final = frozenset(
    {
        "si",
        "feature",
        "gclid",
        "kw",
        "pp",
        "embeds_referring_euri",
        "embeds_referring_origin",
        "source_ve_path",
    }
)
BILIBILI_TRACKING_PARAMS: Final = frozenset(
    {
        "spm_id_from",
        "spmid",
        "from_spmid",
        "from_spm_id",
        "from_source",
        "from",
        "seid",
        "share_source",
        "msource",
        "csource",
        "refer_from",
        "share_from",
        "share_medium",
        "share_plat",
        "share_tag",
        "share_session_id",
        "timestamp",
        "unique_k",
        "vd_source",
        "plat_id",
        "buvid",
        "is_story_h5",
        "up_id",
        "bbid",
        "ts",
        "trackid",
        "track_id",
        "caid",
        "resource_id",
        "source_id",
        "request_id",
        "creative_id",
        "linked_creative_id",
    }
)

PLATFORM_TRACKING_PARAMS: Final[dict[str, frozenset[str]]] = {
    "twitter.com": TWITTER_TRACKING_PARAMS,
    "x.com": TWITTER_TRACKING_PARAMS,
    "pixiv.net": frozenset({"from"}),
    "tiktok.com": frozenset(
        {
            "_d",
            "_r",
            "_t",
            "u_code",
            "preview_pb",
            "timestamp",
            "user_id",
            "sec_user_id",
            "sec_uid",
            "share_app_name",
            "share_app_id",
            "share_author_id",
            "share_iid",
            "share_link_id",
            "source",
            "tt_from",
            "ug_btm",
            "trackparams",
            "share_region",
            "social_share_type",
            "is_from_webapp",
            "sender_device",
            "referer_video_id",
            "embed_source",
            "referer_url",
            "refer",
            "web_id",
            "enter_method",
        }
    ),
    "reddit.com": frozenset(
        {
            "$deep_link",
            "$3p",
            "$original_url",
            "correlation_id",
            "ref_campaign",
            "ref_source",
            "ref",
            "rdt",
            "_branch_match_id",
            "share_id",
            "entry_point",
            "target_user",
            "post_index",
            "post_fullname",
        }
    ),
    "instagram.com": frozenset({"igsh", "igshid", "ig_rid", "stkn", "click_source"}),
    "twitch.tv": frozenset({"tt_medium", "tt_content"}),
    "bsky.app": frozenset({"ref_src"}),
    "facebook.com": frozenset(
        {
            "mibextid",
            "rdid",
            "extid",
            "ref",
            "refsrc",
            "refid",
            "__tn__",
            "__cft__[0]",
            "__xts__[0]",
            "comment_tracking",
            "video_source",
            "action_history",
            "tracking",
            "referral_code",
            "referral_story_type",
            "eav",
            "sfnsn",
            "idorvanity",
            "wtsid",
            "rdc",
            "rdr",
            "paipv",
            "_nc_x",
            "_rdr",
        }
    ),
    "bilibili.com": BILIBILI_TRACKING_PARAMS,
    "b23.tv": BILIBILI_TRACKING_PARAMS,
    "tumblr.com": frozenset({"source"}),
    "threads.net": frozenset({"xmt", "igshid"}),
    "threads.com": frozenset({"xmt", "igshid"}),
    "youtube.com": YOUTUBE_TRACKING_PARAMS,
    "youtu.be": YOUTUBE_TRACKING_PARAMS,
}


def remove_tracking_params(url: str) -> str:
    hostname = urlsplit(url).hostname or ""
    platform_params = next(
        (
            params
            for domain, params in PLATFORM_TRACKING_PARAMS.items()
            if hostname == domain or hostname.endswith(f".{domain}")
        ),
        frozenset(),
    )
    base, fragment_separator, fragment = url.partition("#")
    prefix, query_separator, query = base.partition("?")
    if not query_separator:
        return url

    retained: list[str] = []
    for field in query.split("&"):
        name = unquote_plus(field.partition("=")[0]).lower()
        if (
            name in GLOBAL_TRACKING_PARAMS
            or name in platform_params
            or name.startswith(GLOBAL_TRACKING_PREFIXES)
        ):
            continue
        retained.append(field)

    cleaned_query = "&".join(retained)
    if cleaned_query == query:
        return url
    suffix = f"?{cleaned_query}" if cleaned_query else ""
    return f"{prefix}{suffix}{fragment_separator}{fragment}"
