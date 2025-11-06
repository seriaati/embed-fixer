from __future__ import annotations

from dotenv import load_dotenv

from embed_fixer.core.config import settings

load_dotenv()

TORTOISE_ORM = {
    "connections": {"default": settings.db_uri or "sqlite://embed_fixer.db"},
    "apps": {"embed_fixer": {"models": ["embed_fixer.models", "aerich.models"]}},
}
