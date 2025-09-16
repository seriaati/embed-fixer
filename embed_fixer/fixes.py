from __future__ import annotations

import re
from dataclasses import dataclass
from enum import IntEnum
from typing import Final

EMBEDEZ_NAME = "EmbedEZ"
EMBEDEZ_REPO_URL = "https://embedez.com"


class DomainId(IntEnum):
    TWITTER = 1
    PIXIV = 2
    TIKTOK = 3
    REDDIT = 4
    INSTAGRAM = 5
    FURAFFINITY = 6
    TWITCH_CLIPS = 7
    IWARA = 8
    BLUESKY = 9
    KEMONO = 10
    FACEBOOK = 11
    BILIBILI = 12
    TUMBLR = 13
    THREADS = 14
    PTT = 15


@dataclass(kw_only=True)
class Domain:
    id: DomainId
    name: str
    websites: list[Website]
    fix_methods: list[FixMethod]

    @property
    def default_fix_method(self) -> FixMethod | None:
        if not self.fix_methods:
            return None

        return next((method for method in self.fix_methods if method.default), self.fix_methods[0])

    def get_fix_method(self, fix_id: int) -> FixMethod | None:
        for method in self.fix_methods:
            if method.id == fix_id:
                return method
        return None


@dataclass
class Website:
    pattern: str
    skip_method_ids: list[int] | None = None

    def match(self, url: str) -> bool:
        return re.match(self.pattern, url) is not None


@dataclass(kw_only=True)
class FixMethod:
    id: int
    name: str
    fixes: list[ReplaceFix | AppendURLFix]
    repo_url: str | None = None
    default: bool = False


@dataclass(kw_only=True)
class ReplaceFix:
    old_domain: str
    new_domain: str


@dataclass(kw_only=True)
class AppendURLFix:
    domain: str


DOMAINS: Final[list[Domain]] = [
    Domain(
        id=DomainId.TWITTER,
        name="Twitter/X",
        websites=[
            Website(r"https://(www.)?twitter.com/[a-zA-Z0-9_]+/status/\d+(/photo|video/\d+)?/?"),
            Website(r"https://(www.)?x.com/[a-zA-Z0-9_]+/status/\d+(/photo|video/\d+)?/?"),
        ],
        fix_methods=[
            FixMethod(
                id=1,
                name="FxEmbed",
                fixes=[
                    ReplaceFix(old_domain="twitter.com", new_domain="fxtwitter.com"),
                    ReplaceFix(old_domain="x.com", new_domain="fixupx.com"),
                ],
                repo_url="https://github.com/FxEmbed/FxEmbed",
                default=True,
            ),
            FixMethod(
                id=2,
                name="BetterTwitFix",
                fixes=[
                    ReplaceFix(old_domain="twitter.com", new_domain="vxtwitter.com"),
                    ReplaceFix(old_domain="x.com", new_domain="fixvx.com"),
                ],
                repo_url="https://github.com/dylanpdx/BetterTwitFix",
            ),
            FixMethod(
                id=29,
                name=EMBEDEZ_NAME,
                fixes=[
                    ReplaceFix(old_domain="twitter.com", new_domain="xeezz.com"),
                    ReplaceFix(old_domain="x.com", new_domain="xeezz.com"),
                ],
                repo_url=EMBEDEZ_REPO_URL,
            ),
        ],
    ),
    Domain(
        id=DomainId.PIXIV,
        name="Pixiv",
        websites=[Website(r"https://(www.)?pixiv.net(/[a-zA-Z]+)?/artworks/\d+/?")],
        fix_methods=[
            FixMethod(
                id=3,
                name="Phixiv",
                fixes=[ReplaceFix(old_domain="pixiv.net", new_domain="phixiv.net")],
                repo_url="https://github.com/thelaao/phixiv",
                default=True,
            )
        ],
    ),
    Domain(
        id=DomainId.TIKTOK,
        name="TikTok",
        websites=[
            Website(r"https://(www.)?tiktok.com/(t/\w+|@[\w.]+/video/\d+)/?"),
            Website(r"https://vm.tiktok.com/\w+/?"),
            Website(r"https://vt.tiktok.com/\w+/?"),
        ],
        fix_methods=[
            FixMethod(
                id=4,
                name="fxTikTok",
                fixes=[ReplaceFix(old_domain="tiktok.com", new_domain="tnktok.com")],
                repo_url="https://github.com/okdargy/fxTikTok",
                default=True,
            ),
            FixMethod(
                id=5,
                name="vxtiktok",
                fixes=[ReplaceFix(old_domain="tiktok.com", new_domain="vxtiktok.com")],
                repo_url="https://github.com/dylanpdx/vxtiktok",
            ),
            FixMethod(
                id=27,
                name=EMBEDEZ_NAME,
                fixes=[ReplaceFix(old_domain="tiktok.com", new_domain="tiktokez.com")],
                repo_url=EMBEDEZ_REPO_URL,
            ),
        ],
    ),
    Domain(
        id=DomainId.REDDIT,
        name="Reddit",
        websites=[
            Website(r"https://(www.|old.)?reddit.com/r/[\w]+/comments/[\w]+/[\w]+/?"),
            Website(r"https://(www.|old.)?reddit.com/r/[\w]+/s/[\w]+/?"),
        ],
        fix_methods=[
            FixMethod(
                id=6,
                name="FixReddit",
                fixes=[ReplaceFix(old_domain="reddit.com", new_domain="rxddit.com")],
                repo_url="https://github.com/MinnDevelopment/fxreddit",
                default=True,
            ),
            FixMethod(
                id=7,
                name="vxReddit",
                fixes=[ReplaceFix(old_domain="reddit.com", new_domain="vxreddit.com")],
                repo_url="https://github.com/dylanpdx/vxReddit",
            ),
            FixMethod(
                id=26,
                name=EMBEDEZ_NAME,
                fixes=[ReplaceFix(old_domain="reddit.com", new_domain="redditez.com")],
                repo_url=EMBEDEZ_REPO_URL,
            ),
        ],
    ),
    Domain(
        id=DomainId.INSTAGRAM,
        name="Instagram",
        websites=[
            Website(r"https://(www.)?instagram.com/share/[\w]+/?", skip_method_ids=[8]),
            Website(r"https://(www.)?instagram.com/(p|reels?)/[\w]+/?"),
            Website(r"https://(www.)?instagram.com/share/(p|reels?)/[\w]+/?"),
        ],
        fix_methods=[
            FixMethod(
                id=8,
                name="InstaFix",
                fixes=[ReplaceFix(old_domain="instagram.com", new_domain="uuinstagram.com")],
                repo_url="https://github.com/Wikidepia/InstaFix",
                default=True,
            ),
            FixMethod(
                id=9,
                name=EMBEDEZ_NAME,
                fixes=[ReplaceFix(old_domain="instagram.com", new_domain="g.embedez.com")],
                repo_url=EMBEDEZ_REPO_URL,
            ),
            FixMethod(
                id=23,
                name="KKInstagram",
                fixes=[ReplaceFix(old_domain="instagram.com", new_domain="kkinstagram.com")],
            ),
        ],
    ),
    Domain(
        id=DomainId.FURAFFINITY,
        name="FurAffinity",
        websites=[Website(r"https://(www.)?furaffinity.net/view/\d+/?")],
        fix_methods=[
            FixMethod(
                id=10,
                name="xfuraffinity",
                fixes=[ReplaceFix(old_domain="furaffinity.net", new_domain="xfuraffinity.net")],
                repo_url="https://github.com/FirraWoof/xfuraffinity",
                default=True,
            ),
            FixMethod(
                id=28,
                name="fxraffinity",
                fixes=[ReplaceFix(old_domain="furaffinity.net", new_domain="fxraffinity.net")],
                repo_url="https://fxraffinity.net/",
            ),
        ],
    ),
    Domain(
        id=DomainId.TWITCH_CLIPS,
        name="Twitch Clips",
        websites=[
            Website(r"https://m.twitch.tv/clip/[\w]+/?"),
            Website(r"https://clips.twitch.tv/[\w]+/?"),
            Website(r"https://(www.)?twitch.tv/[\w]+/clip/[\w]+/?"),
        ],
        fix_methods=[
            FixMethod(
                id=11,
                name="fxtwitch",
                fixes=[
                    ReplaceFix(old_domain="clips.twitch.tv", new_domain="fxtwitch.seria.moe/clip"),
                    ReplaceFix(old_domain="m.twitch.tv", new_domain="fxtwitch.seria.moe"),
                    ReplaceFix(old_domain="twitch.tv", new_domain="fxtwitch.seria.moe"),
                ],
                repo_url="https://github.com/seriaati/fxtwitch",
                default=True,
            )
        ],
    ),
    Domain(
        id=DomainId.IWARA,
        name="Iwara",
        websites=[Website(r"https://(www.)?iwara.tv/video/[\w]+/[\w]+/?")],
        fix_methods=[
            FixMethod(
                id=12,
                name="fxiwara",
                fixes=[ReplaceFix(old_domain="iwara.tv", new_domain="fxiwara.seria.moe")],
                repo_url="https://github.com/seriaati/fxiwara",
                default=True,
            )
        ],
    ),
    Domain(
        id=DomainId.BLUESKY,
        name="Bluesky",
        websites=[Website(r"https://(www.)?bsky.app/profile/[\w.-]+/post/[\w]+/?")],
        fix_methods=[
            FixMethod(
                id=13,
                name="VixBluesky",
                fixes=[ReplaceFix(old_domain="bsky.app", new_domain="bskx.app")],
                repo_url="https://github.com/Lexedia/VixBluesky",
                default=True,
            ),
            FixMethod(
                id=14,
                name="FxEmbed",
                fixes=[ReplaceFix(old_domain="bsky.app", new_domain="fxbsky.app")],
                repo_url="https://github.com/FxEmbed/FxEmbed",
            ),
        ],
    ),
    Domain(
        id=DomainId.KEMONO,
        name="Kemono",
        websites=[Website(r"https://(www.)?kemono.su/[a-zA-Z0-9_]+/user/[\w]+/post/[\w]+/?")],
        fix_methods=[],
    ),
    Domain(
        id=DomainId.FACEBOOK,
        name="Facebook",
        websites=[
            Website(r"https://(www.)?facebook.com/(.*)", skip_method_ids=[15]),
            Website(r"https://(www.)?facebook.com/share/r/[\w]+/?"),
            Website(r"https://(www.)?facebook.com/reel/\d+/?"),
            Website(r"https://(www.)?facebook.com/share/v/[\w]+/?"),
        ],
        fix_methods=[
            FixMethod(
                id=15,
                name=EMBEDEZ_NAME,
                fixes=[ReplaceFix(old_domain="facebook.com", new_domain="facebookez.com")],
                repo_url=EMBEDEZ_REPO_URL,
            ),
            FixMethod(
                id=16,
                name="fxfacebook",
                fixes=[ReplaceFix(old_domain="facebook.com", new_domain="fxfb.seria.moe")],
                repo_url="https://github.com/seriaati/fxfacebook",
            ),
            FixMethod(
                id=25,
                name="facebed",
                fixes=[ReplaceFix(old_domain="facebook.com", new_domain="facebed.com")],
                repo_url="https://github.com/4pii4/facebed",
                default=True,
            ),
        ],
    ),
    Domain(
        id=DomainId.BILIBILI,
        name="Bilibili",
        websites=[
            Website(r"https://(www.|m.)?bilibili.com/video/[\w]+/?"),
            Website(r"https://(www.)?b23.tv/[\w]+/?"),
        ],
        fix_methods=[
            FixMethod(
                id=17,
                name="fxbilibili",
                fixes=[
                    ReplaceFix(old_domain="m.bilibili.com", new_domain="fxbilibili.seria.moe"),
                    ReplaceFix(old_domain="bilibili.com", new_domain="fxbilibili.seria.moe"),
                    ReplaceFix(old_domain="b23.tv", new_domain="fxbilibili.seria.moe/b23"),
                ],
                repo_url="https://github.com/seriaati/fxbilibili",
                default=True,
            ),
            FixMethod(
                id=18,
                name=EMBEDEZ_NAME,
                fixes=[ReplaceFix(old_domain="bilibili.com", new_domain="bilibiliez.com")],
                repo_url=EMBEDEZ_REPO_URL,
            ),
            FixMethod(
                id=22,
                name="BiliFix",
                fixes=[
                    ReplaceFix(old_domain="m.bilibili.com", new_domain="vxbilibili.com"),
                    ReplaceFix(old_domain="bilibili.com", new_domain="vxbilibili.com"),
                    ReplaceFix(old_domain="b23.tv", new_domain="vxb23.tv"),
                ],
                repo_url="https://vxbilibili.com",
            ),
        ],
    ),
    Domain(
        id=DomainId.TUMBLR,
        name="Tumblr",
        websites=[
            Website(r"https://(www\.)?tumblr\.com/[a-zA-Z0-9_-]+/[0-9]+/?([a-zA-Z0-9_-]+/?)?")
        ],
        fix_methods=[
            FixMethod(
                id=19,
                name="fxtumblr",
                fixes=[ReplaceFix(old_domain="tumblr.com", new_domain="tpmblr.com")],
                repo_url="https://github.com/knuxify/fxtumblr",
                default=True,
            )
        ],
    ),
    Domain(
        id=DomainId.THREADS,
        name="Threads",
        websites=[
            Website(r"https://(www.)?threads.(net|com)/@[\w.]+/?"),
            Website(r"https://(www.)?threads.(net|com)/@[\w.]+/post/[\w]+/?"),
        ],
        fix_methods=[
            FixMethod(
                id=20,
                name="FixThreads",
                fixes=[
                    ReplaceFix(old_domain="threads.net", new_domain="fixthreads.net"),
                    ReplaceFix(old_domain="threads.com", new_domain="fixthreads.net"),
                ],
                repo_url="https://github.com/milanmdev/fixthreads",
                default=True,
            ),
            FixMethod(
                id=21,
                name="vxThreads",
                fixes=[
                    ReplaceFix(old_domain="threads.net", new_domain="vxthreads.net"),
                    ReplaceFix(old_domain="threads.com", new_domain="vxthreads.net"),
                ],
                repo_url="https://github.com/everettsouthwick/vxThreads",
            ),
            FixMethod(
                id=30,
                name=EMBEDEZ_NAME,
                fixes=[
                    ReplaceFix(old_domain="threads.net", new_domain="threadsez.com"),
                    ReplaceFix(old_domain="threads.com", new_domain="threadsez.com"),
                ],
                repo_url=EMBEDEZ_REPO_URL,
            ),
        ],
    ),
    Domain(
        id=DomainId.PTT,
        name="PTT",
        websites=[Website(r"https://(www.)?ptt.cc/bbs/[A-Za-z0-9_]+/M.\d+.A.[A-Z0-9]+.html/?")],
        fix_methods=[
            FixMethod(
                id=24,
                name="fxptt",
                fixes=[ReplaceFix(old_domain="ptt.cc", new_domain="fxptt.seria.moe")],
                repo_url="https://github.com/seriaati/fxptt",
            )
        ],
    ),
]
