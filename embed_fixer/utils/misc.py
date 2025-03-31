from __future__ import annotations

import io
import re
from urllib.parse import urlparse, urlunparse


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


def remove_query_params(url: str) -> str:
    parsed_url = urlparse(url)
    return urlunparse(
        (
            parsed_url.scheme,
            parsed_url.netloc,
            parsed_url.path,
            parsed_url.params,
            "",
            parsed_url.fragment,
        )
    )


def domain_in_url(url: str, domain: str) -> bool:
    parsed_url = urlparse(url)
    return parsed_url.netloc == domain or parsed_url.netloc.endswith(f".{domain}")


def replace_domain(url: str, old_domain: str, new_domain: str) -> str:
    parsed_url = urlparse(url)
    if parsed_url.netloc == old_domain:
        new_netloc = new_domain
        new_url = parsed_url._replace(netloc=new_netloc)
        return urlunparse(new_url)

    return url
