import re


def extract_urls(text: str) -> list[str]:
    return re.findall(r"https?://\S+", text)
