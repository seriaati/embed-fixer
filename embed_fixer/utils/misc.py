from __future__ import annotations

import asyncio
import io
import re
from typing import Any
from urllib.parse import urlparse, urlunparse


def remove_html_tags(input_string: str) -> str:
    # Use a regex pattern to remove HTML tags
    return re.sub(r"<[^>]*>", "", input_string)


def extract_urls(text: str) -> list[tuple[str, bool]]:
    spoiler_pattern = r"\|\|(https?://[^\s|]+)\|\|"
    regular_pattern = r"(?<!\$)(https?://[^\s]+)"

    spoiler_urls = [(match, True) for match in re.findall(spoiler_pattern, text)]

    text_without_spoilers = re.sub(spoiler_pattern, "", text)
    regular_urls = [(match, False) for match in re.findall(regular_pattern, text_without_spoilers)]

    return spoiler_urls + regular_urls


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
    if domain_in_url(url, old_domain):
        new_url = parsed_url._replace(netloc=new_domain)
        return urlunparse(new_url)

    return url


_tasks_set: set[asyncio.Task[Any] | asyncio.Future[Any]] = set()


def wrap_task_factory() -> None:
    loop = asyncio.get_running_loop()
    original_factory = loop.get_task_factory()

    def new_factory(
        loop: asyncio.AbstractEventLoop, coro: asyncio._CoroutineLike[Any], **kwargs: Any
    ) -> asyncio.Task[Any] | asyncio.Future[Any]:
        if original_factory is not None:
            t = original_factory(loop, coro, **kwargs)
        else:
            t = asyncio.Task(coro, loop=loop, **kwargs)
        _tasks_set.add(t)
        t.add_done_callback(_tasks_set.discard)
        return t

    loop.set_task_factory(new_factory)
