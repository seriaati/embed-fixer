FIX_PATTERNS = (
    r"https://twitter.com/[a-zA-Z0-9_]+/status/\d+",
    r"https://x.com/[a-zA-Z0-9_]+/status/\d+",
    r"https://www.pixiv.net(/[a-zA-Z]+)?/artworks/\d+",
    r"https://www.tiktok.com/(t/\w+|@[\w.]+/video/\d+)",
    r"https://www.reddit.com/r/[\w]+/comments/[\w]+/[\w]+",
    r"https://www.instagram.com/(p|reels?)/[\w]+",
    r"https://www.furaffinity.net/view/\d+",
)
FIXES = {
    "twitter.com": "fxtwitter.com",
    "x.com": "fixupx.com",
    "pixiv.net": "phixiv.net",
    "tiktok.com": "tiktxk.com",
    "reddit.com": "rxddit.com",
    "instagram.com": "ddinstagram.com",
    "furaffinity.net": "xfuraffinity.net",
}
