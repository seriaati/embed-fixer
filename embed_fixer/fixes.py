from __future__ import annotations

import re
from dataclasses import dataclass
from enum import IntEnum
from typing import Final, Literal


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
    fixes: list[Fix]
    repo_url: str | None = None
    default: bool = False


@dataclass(kw_only=True)
class Fix:
    old_domain: str | None = None
    new_domain: str
    method: Literal["replace", "append_url"]


DOMAINS: Final[list[Domain]] = [
    Domain(
        id=DomainId.TWITTER,
        name="Twitter/X",
        websites=[
            Website(r"https://(www.)?twitter.com/[a-zA-Z0-9_]+/status/\d+(/photo|video/\d+)?"),
            Website(r"https://(www.)?x.com/[a-zA-Z0-9_]+/status/\d+(/photo|video/\d+)?"),
        ],
        fix_methods=[
            FixMethod(
                id=1,
                name="FxEmbed",
                fixes=[
                    Fix(old_domain="twitter.com", new_domain="fxtwitter.com", method="replace"),
                    Fix(old_domain="x.com", new_domain="fixupx.com", method="replace"),
                ],
                repo_url="https://github.com/FxEmbed/FxEmbed",
                default=True,
            ),
            FixMethod(
                id=2,
                name="BetterTwitFix",
                fixes=[
                    Fix(old_domain="twitter.com", new_domain="vxtwitter.com", method="replace"),
                    Fix(old_domain="x.com", new_domain="fixvx.com", method="replace"),
                ],
                repo_url="https://github.com/dylanpdx/BetterTwitFix",
            ),
        ],
    ),
    Domain(
        id=DomainId.PIXIV,
        name="Pixiv",
        websites=[Website(r"https://(www.)?pixiv.net(/[a-zA-Z]+)?/artworks/\d+")],
        fix_methods=[
            FixMethod(
                id=3,
                name="Phixiv",
                fixes=[Fix(old_domain="pixiv.net", new_domain="phixiv.net", method="replace")],
                repo_url="https://github.com/thelaao/phixiv",
                default=True,
            )
        ],
    ),
    Domain(
        id=DomainId.TIKTOK,
        name="TikTok",
        websites=[
            Website(r"https://(www.)?tiktok.com/(t/\w+|@[\w.]+/video/\d+)"),
            Website(r"https://vm.tiktok.com/\w+"),
            Website(r"https://vt.tiktok.com/\w+"),
        ],
        fix_methods=[
            FixMethod(
                id=4,
                name="fxTikTok",
                fixes=[Fix(old_domain="tiktok.com", new_domain="tnktok.com", method="replace")],
                repo_url="https://github.com/okdargy/fxTikTok",
                default=True,
            ),
            FixMethod(
                id=5,
                name="vxtiktok",
                fixes=[Fix(old_domain="tiktok.com", new_domain="vxtiktok.com", method="replace")],
                repo_url="https://github.com/dylanpdx/vxtiktok",
            ),
        ],
    ),
    Domain(
        id=DomainId.REDDIT,
        name="Reddit",
        websites=[
            Website(r"https://(www.|old.)?reddit.com/r/[\w]+/comments/[\w]+/[\w]+"),
            Website(r"https://(www.|old.)?reddit.com/r/[\w]+/s/[\w]+"),
        ],
        fix_methods=[
            FixMethod(
                id=6,
                name="FixReddit",
                fixes=[Fix(old_domain="reddit.com", new_domain="rxddit.com", method="replace")],
                repo_url="https://github.com/MinnDevelopment/fxreddit",
                default=True,
            ),
            FixMethod(
                id=7,
                name="vxReddit",
                fixes=[Fix(old_domain="reddit.com", new_domain="vxreddit.com", method="replace")],
                repo_url="https://github.com/dylanpdx/vxReddit",
            ),
        ],
    ),
    Domain(
        id=DomainId.INSTAGRAM,
        name="Instagram",
        websites=[
            Website(r"https://(www.)?instagram.com/share/[\w]+", skip_method_ids=[8]),
            Website(r"https://(www.)?instagram.com/(p|reels?)/[\w]+"),
            Website(r"https://(www.)?instagram.com/share/(p|reels?)/[\w]+"),
        ],
        fix_methods=[
            FixMethod(
                id=8,
                name="InstaFix",
                fixes=[
                    Fix(old_domain="instagram.com", new_domain="ddinstagram.com", method="replace")
                ],
                repo_url="https://github.com/Wikidepia/InstaFix",
                default=True,
            ),
            FixMethod(
                id=9,
                name="EmbedEZ",
                fixes=[Fix(new_domain="embedez.seria.moe/embed", method="append_url")],
                repo_url="https://github.com/seriaati/embedez",
            ),
            FixMethod(
                id=23,
                name="KKInstagram",
                fixes=[
                    Fix(old_domain="instagram.com", new_domain="kkinstagram.com", method="replace")
                ],
            ),
        ],
    ),
    Domain(
        id=DomainId.FURAFFINITY,
        name="FurAffinity",
        websites=[Website(r"https://(www.)?furaffinity.net/view/\d+")],
        fix_methods=[
            FixMethod(
                id=10,
                name="xfuraffinity",
                fixes=[
                    Fix(
                        old_domain="furaffinity.net",
                        new_domain="xfuraffinity.net",
                        method="replace",
                    )
                ],
                repo_url="https://github.com/FirraWoof/xfuraffinity",
                default=True,
            )
        ],
    ),
    Domain(
        id=DomainId.TWITCH_CLIPS,
        name="Twitch Clips",
        websites=[
            Website(r"https://m.twitch.tv/clip/[\w]+"),
            Website(r"https://clips.twitch.tv/[\w]+"),
            Website(r"https://(www.)?twitch.tv/[\w]+/clip/[\w]+"),
        ],
        fix_methods=[
            FixMethod(
                id=11,
                name="fxtwitch",
                fixes=[
                    Fix(
                        old_domain="clips.twitch.tv",
                        new_domain="fxtwitch.seria.moe/clip",
                        method="replace",
                    ),
                    Fix(
                        old_domain="m.twitch.tv", new_domain="fxtwitch.seria.moe", method="replace"
                    ),
                    Fix(old_domain="twitch.tv", new_domain="fxtwitch.seria.moe", method="replace"),
                ],
                repo_url="https://github.com/seriaati/fxtwitch",
                default=True,
            )
        ],
    ),
    Domain(
        id=DomainId.IWARA,
        name="Iwara",
        websites=[Website(r"https://(www.)?iwara.tv/video/[\w]+/[\w]+")],
        fix_methods=[
            FixMethod(
                id=12,
                name="fxiwara",
                fixes=[
                    Fix(old_domain="iwara.tv", new_domain="fxiwara.seria.moe", method="replace")
                ],
                repo_url="https://github.com/seriaati/fxiwara",
                default=True,
            )
        ],
    ),
    Domain(
        id=DomainId.BLUESKY,
        name="Bluesky",
        websites=[Website(r"https://(www.)?bsky.app/profile/[\w.]+/post/[\w]+")],
        fix_methods=[
            FixMethod(
                id=13,
                name="VixBluesky",
                fixes=[Fix(old_domain="bsky.app", new_domain="bskx.app", method="replace")],
                repo_url="https://github.com/Lexedia/VixBluesky",
                default=True,
            ),
            FixMethod(
                id=14,
                name="FxEmbed",
                fixes=[Fix(old_domain="bsky.app", new_domain="fxbsky.app", method="replace")],
                repo_url="https://github.com/FxEmbed/FxEmbed",
            ),
        ],
    ),
    Domain(
        id=DomainId.KEMONO,
        name="Kemono",
        websites=[Website(r"https://(www.)?kemono.su/[a-zA-Z0-9_]+/user/[\w]+/post/[\w]+")],
        fix_methods=[],
    ),
    Domain(
        id=DomainId.FACEBOOK,
        name="Facebook",
        websites=[
            Website(r"https://(www.)?facebook.com/share/r/[\w]+"),
            Website(r"https://(www.)?facebook.com/reel/\d+"),
        ],
        fix_methods=[
            FixMethod(
                id=15,
                name="EmbedEZ",
                fixes=[Fix(new_domain="embedez.seria.moe/embed", method="append_url")],
                default=True,
                repo_url="https://github.com/seriaati/embedez",
            ),
            FixMethod(
                id=16,
                name="fxfacebook",
                fixes=[
                    Fix(old_domain="facebook.com", new_domain="fxfb.seria.moe", method="replace")
                ],
                repo_url="https://github.com/seriaati/fxfacebook",
            ),
        ],
    ),
    Domain(
        id=DomainId.BILIBILI,
        name="Bilibili",
        websites=[
            Website(r"https://(www.|m.)?bilibili.com/video/[\w]+"),
            Website(r"https://(www.)?b23.tv/[\w]+"),
        ],
        fix_methods=[
            FixMethod(
                id=17,
                name="fxbilibili",
                fixes=[
                    Fix(
                        old_domain="m.bilibili.com",
                        new_domain="fxbilibili.seria.moe",
                        method="replace",
                    ),
                    Fix(
                        old_domain="bilibili.com",
                        new_domain="fxbilibili.seria.moe",
                        method="replace",
                    ),
                    Fix(
                        old_domain="b23.tv", new_domain="fxbilibili.seria.moe/b23", method="replace"
                    ),
                ],
                repo_url="https://github.com/seriaati/fxbilibili",
                default=True,
            ),
            FixMethod(
                id=18,
                name="EmbedEZ",
                fixes=[Fix(new_domain="embedez.seria.moe/embed", method="append_url")],
                repo_url="https://github.com/seriaati/embedez",
            ),
            FixMethod(
                id=22,
                name="BiliFix",
                fixes=[
                    Fix(old_domain="m.bilibili.com", new_domain="vxbilibili.com", method="replace"),
                    Fix(old_domain="bilibili.com", new_domain="vxbilibili.com", method="replace"),
                    Fix(old_domain="b23.tv", new_domain="vxb23.tv", method="replace"),
                ],
                repo_url="https://vxbilibili.com",
            ),
        ],
    ),
    Domain(
        id=DomainId.TUMBLR,
        name="Tumblr",
        websites=[Website(r"https://(www.)?tumblr.com/[a-zA-Z0-9_-]+/[0-9]+/[a-zA-Z0-9_-]+")],
        fix_methods=[
            FixMethod(
                id=19,
                name="fxtumblr",
                fixes=[Fix(old_domain="tumblr.com", new_domain="tpmblr.com", method="replace")],
                repo_url="https://github.com/knuxify/fxtumblr",
                default=True,
            )
        ],
    ),
    Domain(
        id=DomainId.THREADS,
        name="Threads",
        websites=[
            Website(r"https://(www.)?threads.(net|com)/@[\w.]+"),
            Website(r"https://(www.)?threads.(net|com)/@[\w.]+/post/[\w]+"),
        ],
        fix_methods=[
            FixMethod(
                id=20,
                name="FixThreads",
                fixes=[
                    Fix(old_domain="threads.net", new_domain="fixthreads.net", method="replace"),
                    Fix(old_domain="threads.com", new_domain="fixthreads.net", method="replace"),
                ],
                repo_url="https://github.com/milanmdev/fixthreads",
                default=True,
            ),
            FixMethod(
                id=21,
                name="vxThreads",
                fixes=[
                    Fix(old_domain="threads.net", new_domain="vxthreads.net", method="replace"),
                    Fix(old_domain="threads.com", new_domain="vxthreads.net", method="replace"),
                ],
                repo_url="https://github.com/everettsouthwick/vxThreads",
            ),
        ],
    ),
]
