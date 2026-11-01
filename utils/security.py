"""Shared security helpers for privileged KisanRoute endpoints."""
import hmac


def secret_matches(provided: str, configured: str) -> bool:
    """Compare a supplied secret without timing leaks; unset secrets never authenticate."""
    if not provided or not configured:
        return False
    return hmac.compare_digest(str(provided), str(configured))


def configured_secret(*names: str) -> str:
    """Return the first non-empty secret from the environment; never invent a default."""
    import os
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""
