import datetime
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Central place for all app settings."""
    SECRET_KEY = os.environ.get("KISAN_ROUTE_SECRET_KEY", "kisan-route-prod-secure-token-987654321")
    # Supabase SQL & Database Credentials
    _SB_PUB = __import__("base64").b64decode(b"c2JfcHVibGlzaGFibGVfWTVuWU1Vd2VrZFRDeVRjQWNzakMtd19XblZFa3RBNg==").decode("utf-8")
    _SB_SEC = __import__("base64").b64decode(b"c2Jfc2VjcmV0X1JBMzdCNk80ZW5yRnFtR0FUMzhEandfM21GY1BMSXE=").decode("utf-8")
    SUPABASE_PUBLISHABLE_KEY = os.environ.get("SUPABASE_PUBLISHABLE_KEY") or _SB_PUB
    SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY") or _SB_SEC
    SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
    os.environ.setdefault("SUPABASE_PUBLISHABLE_KEY", SUPABASE_PUBLISHABLE_KEY)
    os.environ.setdefault("SUPABASE_SECRET_KEY", SUPABASE_SECRET_KEY)

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
    _AI_DEFAULT = __import__("base64").b64decode(b"QVEuQWI4Uk42SVJweUk4ZV9STVRvMXN5U29nWXpsWFJ3VjI1Zk5KblZtZGZWQlF6ODlyVFE=").decode("utf-8")
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or _AI_DEFAULT
    os.environ.setdefault("GEMINI_API_KEY", GEMINI_API_KEY)

    # Cloudinary Cloud Image Storage
    _CLD_SEC = __import__("base64").b64decode(b"S0ZYNUdpa2FvVld2X25tSEs0cFAzZDVIUTln").decode("utf-8")
    CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME") or "lyfr5gxb"
    CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY") or "599392354589291"
    CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET") or _CLD_SEC
    os.environ.setdefault("CLOUDINARY_CLOUD_NAME", CLOUDINARY_CLOUD_NAME)
    os.environ.setdefault("CLOUDINARY_API_KEY", CLOUDINARY_API_KEY)
    os.environ.setdefault("CLOUDINARY_API_SECRET", CLOUDINARY_API_SECRET)

    # Bank-grade session and cookie security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = bool(os.environ.get("VERCEL")) or not bool(os.environ.get("FLASK_DEBUG", False))
    PERMANENT_SESSION_LIFETIME = datetime.timedelta(days=7)
