import datetime
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Central place for all app settings."""
    SECRET_KEY = os.environ.get("KISAN_ROUTE_SECRET_KEY", "kisan-route-prod-secure-token-987654321")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "KISAN_ROUTE_DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'kisanroute.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB upload limit

    # Bank-grade session and cookie security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = bool(os.environ.get("VERCEL")) or not bool(os.environ.get("FLASK_DEBUG", False))
    PERMANENT_SESSION_LIFETIME = datetime.timedelta(days=7)
