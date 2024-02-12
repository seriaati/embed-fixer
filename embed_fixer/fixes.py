FIX_PATTERNS = {
    "twitter.com": r"https://twitter.com/[a-zA-Z0-9_]+/status/\d+",
    "x.com": r"https://x.com/[a-zA-Z0-9_]+/status/\d+",
    "pixiv.net": r"https://www.pixiv.net/[a-zA-Z]+/artworks/\d+",
    "tiktok.com": r"https://www.tiktok.com/@[\w]+/video/\d+",
    "reddit.com": r"https://www.reddit.com/r/[\w]+/comments/[\w]+/[\w]+",
    "instagram.com/p": r"https://www.instagram.com/p/[\w]+",
    "instagram.com/reels": r"https://www.instagram.com/reels/[\w]+",
}
FIXES = {
    "twitter.com": "fxtwitter.com",
    "x.com": "fixupx.com",
    "pixiv.net": "phixiv.net",
    "tiktok.com": "tiktxk.com",
    "reddit.com": "rxddit.com",
    "instagram.com": "ddinstagram.com",
}
