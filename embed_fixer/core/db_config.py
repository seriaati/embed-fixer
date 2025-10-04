from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

TORTOISE_ORM = {
    "connections": {"default": os.getenv("DB_URI") or "sqlite://embed_fixer.db"},
    "apps": {"embed_fixer": {"models": ["embed_fixer.models", "aerich.models"]}},
}
