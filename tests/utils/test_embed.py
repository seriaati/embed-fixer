from __future__ import annotations

import discord
import pytest

from embed_fixer.utils.embed import DefaultEmbed, ErrorEmbed


@pytest.mark.parametrize(
    ("embed_type", "color"), [(DefaultEmbed, 9685757), (ErrorEmbed, discord.Color.red().value)]
)
@pytest.mark.parametrize(("title", "description"), [(None, None), ("Title", "Description")])
def test_embed_helpers_set_color_and_optional_text(
    embed_type: type[discord.Embed], color: int, title: str | None, description: str | None
) -> None:
    embed = embed_type(title=title, description=description)
    assert embed.color is not None
    assert embed.color.value == color
    assert embed.title == title
    assert embed.description == description
    assert embed.to_dict().get("type") == "rich"
