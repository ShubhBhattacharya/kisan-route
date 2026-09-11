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
