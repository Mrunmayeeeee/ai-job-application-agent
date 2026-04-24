"""
Central configuration for the AI Job Application Agent.
All settings are loaded from environment variables with sensible defaults.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""

    # ── OpenAI ───────────────────────────────────────────────────────
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))

    # ── Flask ────────────────────────────────────────────────────────
    FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "true").lower() == "true"

    # ── LinkedIn ─────────────────────────────────────────────────────
    LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL", "")
    LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")

    # ── Internshala ──────────────────────────────────────────────────
    INTERNSHALA_EMAIL = os.getenv("INTERNSHALA_EMAIL", "")
    INTERNSHALA_PASSWORD = os.getenv("INTERNSHALA_PASSWORD", "")

    # ── Scraper ──────────────────────────────────────────────────────
    SCRAPE_DELAY = int(os.getenv("SCRAPE_DELAY_SECONDS", "3"))
    MAX_JOBS_PER_SCRAPE = int(os.getenv("MAX_JOBS_PER_SCRAPE", "50"))
    HEADLESS = os.getenv("HEADLESS_BROWSER", "true").lower() == "true"

    # ── Paths ────────────────────────────────────────────────────────
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
    DB_PATH = os.path.join(BASE_DIR, "applications.db")
    COVER_LETTERS_DIR = os.path.join(BASE_DIR, "cover_letters")

    @classmethod
    def ensure_dirs(cls):
        """Create required directories if they don't exist."""
        for d in [cls.UPLOAD_DIR, cls.COVER_LETTERS_DIR]:
            os.makedirs(d, exist_ok=True)
