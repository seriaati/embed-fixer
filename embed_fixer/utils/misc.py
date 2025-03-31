from __future__ import annotations

import io
import re


def remove_html_tags(input_string: str) -> str:
    # Use a regex pattern to remove HTML tags
    clean_text = re.sub(r"<[^>]*>", "", input_string)
    return clean_text


def extract_urls(text: str) -> list[str]:
    return re.findall(
        r"(?<!\$)http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
        text,
    )


def get_filesize(fp: io.BufferedIOBase) -> int:
    original_pos = fp.tell()
    fp.seek(0, io.SEEK_END)
    size = fp.tell()
    fp.seek(original_pos)
    return size
