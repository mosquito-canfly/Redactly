"""Gemini connectivity check and vision-based sensitive region detection."""

import json
import mimetypes
import time

from google import genai
from google.genai import errors, types
from PIL import Image

from redactly.config import require_gemini_key

# gemini-2.5-flash returns 404 for this account (deprecated for new users) —
# reusing the model that test_connection() already confirmed works.
MODEL = "gemini-flash-latest"


def _is_retryable(e: Exception) -> bool:
    """True for transient errors worth retrying: 429/503, or a connection reset."""
    if isinstance(e, errors.APIError) and e.code in (429, 503):
        return True
    if isinstance(e, (ConnectionError, TimeoutError)):
        return True
    text = str(e)
    return "RESOURCE_EXHAUSTED" in text or "UNAVAILABLE" in text or "10054" in text


def call_with_retry(fn, *args, max_retries: int = 5, base_delay: float = 2.0, **kwargs):
    """Call fn(*args, **kwargs), retrying on transient errors with exponential backoff.

    Retries only rate-limit (429), unavailable (503), and connection-reset
    errors. Anything else re-raises immediately — this is not a general
    error-swallower. Re-raises the last error if all retries are exhausted;
    callers are expected to already catch and degrade gracefully.
    """
    for attempt in range(max_retries):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if not _is_retryable(e) or attempt == max_retries - 1:
                raise
            delay = base_delay * 2**attempt
            print(f"NOTE: transient Gemini error ({e}); retrying in {delay:.0f}s...")
            time.sleep(delay)

_DETECT_PROMPT = """You are a privacy redaction assistant. Find every region in \
this image containing sensitive personal information: ID/IC numbers, faces, \
full names, addresses, emails, phone numbers, account numbers, signatures.

Also find passwords and credential fields: any text inside or directly below \
a field labeled "password", "passcode", "PIN", or similar is sensitive and its \
region must be returned — including cases where a "show password" toggle has \
revealed it as plain text. Also detect other credential-like secrets: API keys, \
tokens, security codes, and OTPs.

The image is exactly {width}x{height} pixels. Return coordinates in real \
pixels within those bounds (left/top from 0,0, no rescaling).

Return ONLY valid JSON, no markdown, no commentary: a list of objects like:
[{{"label": "email", "box": {{"left": 10, "top": 20, "width": 100, "height": 15}}}}]
If nothing is found, return []."""


def test_connection() -> str:
    """Send a trivial prompt to Gemini and return its response, or an ERROR: string."""
    try:
        client = genai.Client(api_key=require_gemini_key())
        response = client.models.generate_content(
            model=MODEL,
            contents="Reply with exactly the word: OK",
        )
        return response.text
    except Exception as e:
        return f"ERROR: {e}"


def _parse_regions(text: str) -> list[dict]:
    """Parse Gemini's JSON response (possibly wrapped in ```/```json fences)."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        text = text.rsplit("```", 1)[0]

    try:
        items = json.loads(text)
    except json.JSONDecodeError:
        return []

    boxes = []
    for item in items:
        try:
            box = item["box"]
            boxes.append({
                "label": item["label"],
                "left": int(box["left"]),
                "top": int(box["top"]),
                "width": int(box["width"]),
                "height": int(box["height"]),
            })
        except (KeyError, TypeError, ValueError):
            continue  # skip malformed items rather than crash
    return boxes


def detect_sensitive_regions(image_path: str) -> list[dict]:
    """Ask Gemini to find sensitive regions in an image.

    Returns a list of dicts with keys: label, left, top, width, height.
    Returns an empty list (never raises) on API errors or unparsable output.
    """
    width, height = Image.open(image_path).size
    mime_type = mimetypes.guess_type(image_path)[0] or "image/png"

    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        client = genai.Client(api_key=require_gemini_key())
        response = call_with_retry(
            client.models.generate_content,
            model=MODEL,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                _DETECT_PROMPT.format(width=width, height=height),
            ],
        )
        return _parse_regions(response.text)
    except Exception as e:
        print(f"WARNING: Gemini region detection failed: {e}")
        return []


if __name__ == "__main__":
    # ponytail: smallest possible self-check, not a test suite
    assert _parse_regions('[{"label": "email", "box": {"left": 1, "top": 2, "width": 3, "height": 4}}]') == \
        [{"label": "email", "top": 2, "left": 1, "width": 3, "height": 4}]
    assert _parse_regions('```json\n[{"label": "x", "box": {"left": 0, "top": 0, "width": 1, "height": 1}}]\n```') != []
    assert _parse_regions("not json") == []
    assert _parse_regions('[{"label": "bad"}]') == []  # missing box, skipped not crashed

    # call_with_retry: succeeds after transient failures, doesn't retry real errors
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise errors.ServerError(503, {"error": {"message": "UNAVAILABLE"}})
        return "ok"

    assert call_with_retry(flaky, base_delay=0.01) == "ok"
    assert calls["n"] == 3

    def always_fails_retryable():
        raise ConnectionResetError("connection reset")

    try:
        call_with_retry(always_fails_retryable, max_retries=2, base_delay=0.01)
        assert False, "should have raised after exhausting retries"
    except ConnectionResetError:
        pass

    calls["n"] = 0

    def counts_then_fails():
        calls["n"] += 1
        raise ValueError("bad input")

    try:
        call_with_retry(counts_then_fails, base_delay=0.01)
        assert False, "should have raised immediately"
    except ValueError:
        assert calls["n"] == 1  # no retries for a non-retryable error
    print("llm.py self-check passed")
