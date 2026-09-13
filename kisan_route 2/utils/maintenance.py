"""Maintenance Mode Engine for Kisan Route.
Allows seamless toggling of system maintenance status with admin bypass.
"""

import os

ADMIN_SECRET_KEYS = {"kisan_admin_2026", "123456", "admin123"}
FLAG_PATHS = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "maintenance.flag"),
    "/tmp/maintenance.flag",
]

_IN_MEMORY_MAINTENANCE = False


def is_maintenance_mode() -> bool:
    """Check if Maintenance Mode is active via env, file flags, or memory."""
    # 1. Check environment variable
    env_val = os.environ.get("MAINTENANCE_MODE", "").strip().lower()
    if env_val in ("true", "1", "yes", "on"):
        return True

    # 2. Check in-memory flag
    global _IN_MEMORY_MAINTENANCE
    if _IN_MEMORY_MAINTENANCE:
        return True

    # 3. Check flag files
    for p in FLAG_PATHS:
        try:
            if os.path.exists(p):
                return True
        except Exception:
            pass

    return False


def set_maintenance_mode(active: bool) -> bool:
    """Turn Maintenance Mode ON or OFF."""
    global _IN_MEMORY_MAINTENANCE
    _IN_MEMORY_MAINTENANCE = bool(active)

    for p in FLAG_PATHS:
        try:
            parent = os.path.dirname(p)
            if active:
                if parent and os.path.exists(parent):
                    with open(p, "w", encoding="utf-8") as f:
                        f.write("MAINTENANCE_ACTIVE")
            else:
                if os.path.exists(p):
                    os.remove(p)
        except Exception as e:
            print(f"Maintenance flag update skipped for {p}: {e}")

    return is_maintenance_mode()


def is_bypass_authorized(secret: str) -> bool:
    """Validate admin / developer secret key for bypassing maintenance mode."""
    if not secret:
        return False
    configured_key = os.environ.get("MAINTENANCE_SECRET_KEY", "")
    if configured_key and secret.strip() == configured_key.strip():
        return True
    return secret.strip() in ADMIN_SECRET_KEYS
