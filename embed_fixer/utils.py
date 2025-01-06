from __future__ import annotations

import re


def remove_html_tags(input_string: str) -> str:
    # Use a regex pattern to remove HTML tags
    clean_text = re.sub(r"<[^>]*>", "", input_string)
    return clean_text
