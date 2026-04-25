"""
AI Job Application Agent - Main Entry Point
Starts the Flask web dashboard with all routes and agent capabilities.
"""

import sys
import os
import logging

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from config import Config
from web.app import app

# Ensure required directories exist (needed for gunicorn/production)
Config.ensure_dirs()

# -- Logging Setup --
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-20s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


def check_setup():
    """Verify environment is correctly configured."""
    issues = []

    if not Config.OPENAI_API_KEY or Config.OPENAI_API_KEY.startswith("sk-your"):
        issues.append(
            "[!] OPENAI_API_KEY not set. AI features (matching, cover letters, chat) will be disabled.\n"
            "    -> Copy .env.example to .env and add your API key."
        )

    Config.ensure_dirs()

    if issues:
        print("\n" + "=" * 60)
        print("  SETUP NOTES")
        print("=" * 60)
        for issue in issues:
            print(f"\n  {issue}")
        print("\n" + "=" * 60)
        print("  The dashboard will still work for scraping and tracking.")
        print("=" * 60 + "\n")
    else:
        print("\n  [OK] All configured. Starting AI Job Application Agent...\n")


# -- Template Context Processor --
@app.context_processor
def inject_globals():
    """Inject global variables into all templates."""
    from database.models import Database
    db = Database()
    return {
        "stats": db.get_stats(),
        "config_status": bool(Config.OPENAI_API_KEY and not Config.OPENAI_API_KEY.startswith("sk-your")),
    }


if __name__ == "__main__":
    check_setup()

    print("  AI Job Application Agent")
    print("  Dashboard: http://localhost:5000")
    print("  Press Ctrl+C to stop\n")

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=Config.FLASK_DEBUG,
    )
