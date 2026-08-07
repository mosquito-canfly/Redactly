"""Regex-based classification of sensitive text."""

import re

# Named so new patterns can be added without touching the matching logic.
PATTERNS = {
    # user@domain.tld
    "email": re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"),
    # 13-16 digits, spaces/dashes allowed between digits
    "credit_card": re.compile(r"^(?:\d[ -]?){13,16}$"),
    # local/international phone numbers: optional +country code, 7-15 digits total
    "phone": re.compile(r"^\+?\d{1,3}?[ -]?\(?\d{2,4}\)?[ -]?\d{3,4}[ -]?\d{3,4}$"),
    # 20+ alphanumeric chars containing at least one letter and one digit (API-key-like)
    "api_key": re.compile(r"^(?=[A-Za-z0-9]{20,}$)(?=.*[A-Za-z])(?=.*\d)[A-Za-z0-9]+$"),
    # Malaysian IC/MyKad/NRIC, YYMMDD-PB-###G, e.g. 890724-01-2498 or 890724012498
    "malaysian_ic": re.compile(r"^\d{6}-\d{2}-\d{4}$|^\d{12}$"),
    # IPv4 address, e.g. 192.168.1.1
    "ipv4": re.compile(r"^(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$"),
    # fallback: 9+ consecutive digits (account/reference numbers) — disable by deleting this entry if noisy
    "long_number": re.compile(r"^\d{9,}$"),
}


def is_sensitive_regex(text: str) -> bool:
    """Return True if text matches any high-confidence sensitive pattern."""
    text = text.strip()
    return any(pattern.match(text) for pattern in PATTERNS.values())


def filter_sensitive_boxes(boxes: list[dict]) -> list[dict]:
    """Return only the boxes whose text is flagged as sensitive."""
    return [box for box in boxes if is_sensitive_regex(box["text"])]


if __name__ == "__main__":
    # ponytail: smallest possible self-check, not a test suite
    assert is_sensitive_regex("inyee2005@gmail.com")
    assert is_sensitive_regex("4111-1111-1111-1111")
    assert is_sensitive_regex("+1 415-555-1234")
    assert is_sensitive_regex("AbCdEfGh12345678901234xyz")
    assert is_sensitive_regex("890724-01-2498")
    assert is_sensitive_regex("890724012498")
    assert is_sensitive_regex("192.168.1.1")
    assert is_sensitive_regex("123456789")
    assert not is_sensitive_regex("Welcome")
    assert not is_sensitive_regex("password")
    assert not is_sensitive_regex("999.999.999.999")
    print("classify.py self-check passed")
