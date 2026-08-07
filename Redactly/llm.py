"""Gemini connectivity check."""

from google import genai

from redactly.config import require_gemini_key

_MODEL = "gemini-flash-latest"


def test_connection() -> str:
    """Send a trivial prompt to Gemini and return its response, or an ERROR: string."""
    try:
        client = genai.Client(api_key=require_gemini_key())
        response = client.models.generate_content(
            model=_MODEL,
            contents="Reply with exactly the word: OK",
        )
        return response.text
    except Exception as e:
        return f"ERROR: {e}"
