from __future__ import annotations

import asyncio
import runpy
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

import ci
from embed_fixer.fixes import DOMAINS
from embed_fixer.settings import GuildSetting

if TYPE_CHECKING:
    from types import CoroutineType


@pytest.mark.parametrize("bullet", ["-", "*"])
def test_readme_replacement_preserves_surrounding_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bullet: str
) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        f"intro\n## section\nheader\n\n{bullet} old\n{bullet} other\n\nnext\n", encoding="utf-8"
    )
    monkeypatch.setattr(ci, "README", readme)
    ci.update_readme_bullet_points(
        ["new", "second"], section_start_marker="## section", list_header_marker="header"
    )
    assert (
        readme.read_text(encoding="utf-8")
        == "intro\n## section\nheader\n\n- new\n- second\n\nnext\n"
    )


@pytest.mark.parametrize(
    ("text", "error"),
    [
        (None, FileNotFoundError),
        ("missing", ValueError),
        ("section\nmissing", ValueError),
        ("section\nheader\n\nparagraph\n- later", ValueError),
        ("section\nheader\n\n", ValueError),
    ],
)
def test_readme_update_failure_preserves_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, text: str | None, error: type[Exception]
) -> None:
    readme = tmp_path / "README.md"
    monkeypatch.setattr(ci, "README", readme)
    if text is not None:
        readme.write_text(text, encoding="utf-8")
    with pytest.raises(error):
        ci.update_readme_bullet_points(
            ["new"], section_start_marker="section", list_header_marker="header"
        )
    if text is not None:
        assert readme.read_text(encoding="utf-8") == text


async def test_ci_updates_all_real_settings_and_domain_bullets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        "## Very Customizable\nBelow are settings you can change with the `/settings` command:\n\n- old\n\n## Embed Fixing\nFixings are currently available for:\n\n- old\n\nfooter\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ci, "README", readme)
    await ci.run_ci()
    content = readme.read_text(encoding="utf-8")
    assert content.count("\n- ") == len(GuildSetting) + len(DOMAINS)
    for domain in DOMAINS:
        assert f"**{domain.name}**:" in content
    assert "Media extraction only, no embed fixing" in content
    assert "([disabled by default](#about-youtube-embed-fixing))" in content
    assert "https://github.com/dededecline/embed-fixer#about-youtube-embed-fixing" in content
    assert "github.com/seriaati/embed-fixer" not in content
    assert content.endswith("footer\n")


def test_script_entrypoint_schedules_ci_coroutine(monkeypatch: pytest.MonkeyPatch) -> None:

    scheduled: list[str] = []

    def capture_run(coroutine: CoroutineType[object, object, object]) -> None:
        scheduled.append(coroutine.cr_code.co_name)
        coroutine.close()

    monkeypatch.setattr(asyncio, "run", capture_run)
    runpy.run_path(str(Path(ci.__file__)), run_name="__main__")
    assert scheduled == ["run_ci"]
