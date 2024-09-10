from __future__ import annotations

FIX_PATTERNS = (
    r"https://twitter.com/[a-zA-Z0-9_]+/status/\d+",
    r"https://x.com/[a-zA-Z0-9_]+/status/\d+",
    r"https://www.pixiv.net(/[a-zA-Z]+)?/artworks/\d+",
    r"https://www.tiktok.com/(t/\w+|@[\w.]+/video/\d+)",
    r"https://vm.tiktok.com/\w+",
    r"https://vt.tiktok.com/\w+",
    r"https://www.reddit.com/r/[\w]+/comments/[\w]+/[\w]+",
    r"https://www.instagram.com/(p|reels?)/[\w]+",
    r"https://www.furaffinity.net/view/\d+",
    r"https://m.twitch.tv/clip/[\w]+",
    r"https://clips.twitch.tv/[\w]+",
)
FIXES = {
    "twitter.com": "fxtwitter.com",
    "x.com": "fixupx.com",
    "pixiv.net": "phixiv.net",
    "tiktok.com": "vxtiktok.com",
    "reddit.com": "rxddit.com",
    "instagram.com": "ddinstagram.com",
    "furaffinity.net": "xfuraffinity.net",
    "clips.twitch.tv": "fxtwitch.seriaati.xyz/clip",
    "m.twitch.tv": "fxtwitch.seriaati.xyz",
}
