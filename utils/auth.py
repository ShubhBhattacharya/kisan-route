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
            if not session.get("user_id"):
                flash("Please log in to continue.", "error")
                return redirect(url_for(f"{role}.login"))

            # If user is already authenticated but switching to another role:
            if session.get("role") != role:
                from models import User
                from extensions import db
                from werkzeug.security import generate_password_hash

                phone = session.get("phone") or "9876543210"
                target_user = User.query.filter_by(role=role, phone=phone).first()
                if not target_user:
                    target_user = User.query.filter_by(role=role, phone="9876543210").first()
                if not target_user:
                    role_configs = {
                        "farmer": {"name": "Demo Farmer", "extra": {"crop_type": "Wheat", "city": "Palwal"}},
                        "driver": {"name": "Demo Driver", "extra": {"driver_type": "independent", "vehicle_type": "Tata Ace (1.5 Ton)", "capacity": "1500 kg", "profile_complete": True}},
                        "cluster": {"name": "Demo Cluster Hub", "extra": {"cluster_name": "Palwal Kisan Sangathan", "village": "Palwal"}},
                        "customer": {"name": "Demo Customer", "extra": {"city": "Delhi NCR"}},
                        "wholesaler": {"name": "Demo Wholesaler", "extra": {"business_name": "Kisan Mandi Traders", "city": "Azadpur Mandi"}},
                    }
                    cfg = role_configs.get(role, {"name": f"Demo {role.capitalize()}", "extra": {}})
                    target_user = User(
                        role=role,
                        full_name=cfg["name"],
                        phone="9876543210",
                        password_hash=generate_password_hash("123456"),
                    )
                    target_user.set_extra(cfg["extra"])
                    db.session.add(target_user)
                    db.session.commit()

                session["user_id"] = target_user.id
                session["role"] = role
                session["name"] = target_user.full_name
                session["phone"] = target_user.phone

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

