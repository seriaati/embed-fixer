from __future__ import annotations

from discord import Embed


class DefaultEmbed(Embed):
    def __init__(
        self,
        *,
        title: str | None = None,
        description: str | None = None,
    ) -> None:
        super().__init__(
            color=9685757,
            title=title,
            description=description,
        )


class ErrorEmbed(Embed):
    def __init__(
        self,
        *,
        title: str | None = None,
        description: str | None = None,
    ) -> None:
        super().__init__(
            color=54327,
            title=title,
            description=description,
        )
