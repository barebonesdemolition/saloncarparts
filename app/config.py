import os
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

if ENV_PATH.exists():
    with open(ENV_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value


class Settings:
    APP_NAME = "Salon AutoZone & AutoTrader"
    APP_VERSION = "1.0.0"
    DEFAULT_CURRENCY = "SLL"
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./saloncarparts.db")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "salon-autozone-secret-change-in-prod")
    # Read GEMINI_API_KEY from environment (works for both AIzaSy and AQ. formats)
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


def get_settings():
    return Settings()
