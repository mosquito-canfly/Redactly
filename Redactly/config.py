"""Loads configuration from environment / .env file."""

import os

from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


def require_gemini_key() -> str:
    """Return the Gemini API key, or raise a friendly error if it's not set."""
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Create a .env file in the project root "
            "(see .env.example) with a line like:\n  GEMINI_API_KEY=your_key_here"
        )
    return GEMINI_API_KEY
