from typing import Literal

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"


class Settings(BaseSettings):
    sentry_dsn: str | None = None
    redis_url: str | None = None
    discord_token: str
    db_uri: str
    env: Literal["dev", "prod"] = "dev"
    user_agent: str = USER_AGENT
    proxy_url: str | None = None
    heartbeat_url: str | None = None
    pixiv_session_id: str | None = None

    @property
    def pixiv_headers(self) -> dict[str, str]:
        headers = {"Referer": "https://www.pixiv.net/", "User-Agent": self.user_agent}
        if self.pixiv_session_id:
            headers["Cookie"] = f"PHPSESSID={self.pixiv_session_id}"
        return headers


load_dotenv()
settings = Settings()  # pyright: ignore[reportCallIssue]
