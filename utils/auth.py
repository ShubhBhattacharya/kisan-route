"""Simple session-based login guard, shared by every role blueprint.

Each role blueprint is named after its role (e.g. `farmer`, `driver`), and
each defines a `login` view — so `login_required('farmer')` can always
redirect to `farmer.login` by convention.
"""
from functools import wraps

from flask import flash, redirect, session, url_for


def login_required(role: str):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if session.get("role") != role or not session.get("user_id"):
                flash("Please log in to continue.", "error")
                return redirect(url_for(f"{role}.login"))
            return view_func(*args, **kwargs)
        return wrapped
    return decorator


def clean_phone(phone: str) -> str:
    """Normalize Indian phone input:
    - Strip all non-numeric characters (+, -, spaces, parentheses)
    - Remove leading zeros
    - Strip country code '91' if 12 digits
    - Return strictly the 10-digit phone number (e.g. 8700257488)
    """
    if not phone:
        return ""
    import re
    digits = re.sub(r"\D", "", str(phone).strip()).lstrip("0")
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    return digits[-10:] if len(digits) >= 10 else digits


def is_valid_phone(phone: str) -> bool:
    """Validate phone number: must be non-empty and exactly 10 numeric digits."""
    if not phone:
        return False
    cleaned = clean_phone(phone)
    import re
    return bool(re.match(r"^[6-9]\d{9}$", cleaned) or (len(cleaned) == 10 and cleaned.isdigit()))

