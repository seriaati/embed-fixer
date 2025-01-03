from __future__ import annotations

FIX_PATTERNS = (
    r"https://(www.)?twitter.com/[a-zA-Z0-9_]+/status/\d+(/photo|video/\d+)?",
    r"https://(www.)?x.com/[a-zA-Z0-9_]+/status/\d+(/photo|video/\d+)?",
    r"https://(www.)?pixiv.net(/[a-zA-Z]+)?/artworks/\d+",
    r"https://(www.)?tiktok.com/(t/\w+|@[\w.]+/video/\d+)",
    r"https://vm.tiktok.com/\w+",
    r"https://vt.tiktok.com/\w+",
    r"https://(www.)?reddit.com/r/[\w]+/comments/[\w]+/[\w]+",
    r"https://(www.)?reddit.com/r/[\w]+/s/[\w]+",
    r"https://(www.)?instagram.com/(p|reels?)/[\w]+",
    r"https://(www.)?instagram.com/share/(p|reel?)/[\w]+",
    r"https://(www.)?furaffinity.net/view/\d+",
    r"https://m.twitch.tv/clip/[\w]+",
    r"https://clips.twitch.tv/[\w]+",
    r"https://(www.)?iwara.tv/video/[\w]+/[\w]+",
    r"https://(www.)?twitch.tv/[\w]+/clip/[\w]+",
    r"https://(www.)?bsky.app/profile/[\w.]+/post/[\w]+",
    r"https://(www.)?kemono.su/[a-zA-Z0-9_]+/user/[\w]+/post/[\w]+",
)
FIXES = {
    "twitter.com": "fxtwitter.com",
    "x.com": "fixupx.com",
    "pixiv.net": "phixiv.net",
    "tiktok.com": "vxtiktok.com",
    "reddit.com": "rxddit.com",
    "instagram.com": "instagramez.com",
    "furaffinity.net": "xfuraffinity.net",
    "clips.twitch.tv": "fxtwitch.seria.moe/clip",
    "m.twitch.tv": "fxtwitch.seria.moe",
    "www.iwara.tv": "fxiwara.seria.moe",
    "www.twitch.tv": "fxtwitch.seria.moe",
    "bsky.app": "bskx.app",
    "kemono.su": "kemono.su",
}
