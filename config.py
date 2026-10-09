import datetime
import os
import secrets

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Central place for all app settings."""
    # Cryptographically secure random secret key if not set in environment
    SECRET_KEY = os.environ.get("KISAN_ROUTE_SECRET_KEY") or os.environ.get("SECRET_KEY") or secrets.token_hex(32)

    # Supabase SQL & Database Credentials (strictly from environment)
    SUPABASE_PUBLISHABLE_KEY = os.environ.get("SUPABASE_PUBLISHABLE_KEY", "")
    SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY", "")
    SUPABASE_URL = os.environ.get("SUPABASE_URL", "")

    # Database URI (supports SQLite locally, Supabase PostgreSQL in Cloud)
    _raw_db = (
        os.environ.get("SUPABASE_DB_URL")
        or os.environ.get("KISAN_ROUTE_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or f"sqlite:///{os.path.join(BASE_DIR, 'kisanroute.db')}"
    )
    if _raw_db.startswith("postgres://"):
        _raw_db = _raw_db.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = _raw_db

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB upload limit

    # AI Model Key (Gemini)
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

    # Cloudinary Cloud Image Storage
    CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
    CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY", "")
    CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET", "")

    # Mandi Bhav & Live Commodity Rates API
    MANDI_API_KEY = os.environ.get("MANDI_API_KEY") or os.environ.get("RAPIDAPI_KEY", "")
    MANDI_API_HOST = os.environ.get("MANDI_API_HOST", "")
    MANDI_API_URL = os.environ.get("MANDI_API_URL", "")

    # OpenRouteService (ORS) - Live Map & Route Optimization
    OPENROUTESERVICE_KEY = os.environ.get("OPENROUTESERVICE_KEY") or os.environ.get("ORS_API_KEY", "")

    # WhatsApp Direct Handshake Authentication
    WHATSAPP_RECEIVER_NUMBER = os.environ.get("WHATSAPP_RECEIVER_NUMBER", "918700257488")

    # Bank-grade session and cookie security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = bool(os.environ.get("VERCEL")) or not bool(os.environ.get("FLASK_DEBUG", False))
    PERMANENT_SESSION_LIFETIME = datetime.timedelta(days=7)
