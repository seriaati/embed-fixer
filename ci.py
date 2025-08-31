from __future__ import annotations

import asyncio
from pathlib import Path

from loguru import logger

from embed_fixer.fixes import DOMAINS
from embed_fixer.settings import Setting
from embed_fixer.translator import Translator

README = Path(__file__).parent / "README.md"
LANG = "en_US"


def update_readme_bullet_points(
    new_items: list[str], *, section_start_marker: str, list_header_marker: str
) -> None:
    if not README.exists():
        msg = f"README file not found at {README}"
        raise FileNotFoundError(msg)

    with README.open(encoding="utf-8") as f:
        lines = f.read().splitlines()

    try:
        section_start_index = lines.index(section_start_marker)
        list_header_index = lines.index(list_header_marker, section_start_index)
    except ValueError as e:
        msg = f"Could not find the specified section or list header in README: {e}"
        raise ValueError(msg) from e

    list_start_index = -1
    for i in range(list_header_index + 1, len(lines)):
        if lines[i].strip().startswith(("-", "*")):
            list_start_index = i
            break
        if lines[i].strip():
            break

    if list_start_index == -1:
        msg = "Could not find the start of the bulleted list to replace."
        raise ValueError(msg)

    list_end_index = list_start_index
    while list_end_index < len(lines) and lines[list_end_index].strip().startswith(("-", "*")):
        list_end_index += 1

    new_bullet_lines = [f"- {setting}" for setting in new_items]
    updated_lines = lines[:list_start_index] + new_bullet_lines + lines[list_end_index:]

    with README.open("w", encoding="utf-8") as f:
        f.write("\n".join(updated_lines))
        f.write("\n")


async def run_ci() -> None:
    translator = Translator()
    await translator.load()

    updated_settings = [
        f"**{translator.get(LANG, s.value)}**: {translator.get(LANG, f'{s.value}_desc')}"
        for s in Setting
    ]
    update_readme_bullet_points(
        updated_settings,
        section_start_marker="## Very Customizable",
        list_header_marker="Below are settings you can change with the `/settings` command:",
    )
    logger.success("Successfully updated settings in README.")

    updated_domains = [
        f"**{domain.name}**: {'/'.join(f'[{fix.name}]({fix.repo_url})' if fix.repo_url else fix.name for fix in domain.fix_methods) or 'Media extraction only, no embed fixing'}"
        for domain in DOMAINS
    ]
    update_readme_bullet_points(
        updated_domains,
        section_start_marker="## Embed Fixing",
        list_header_marker="Fixings are currently available for:",
    )
    logger.success("Successfully updated domains in README.")


if __name__ == "__main__":
    asyncio.run(run_ci())
