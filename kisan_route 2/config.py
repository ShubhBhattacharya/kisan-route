import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Central place for all app settings.

    For the hackathon prototype these are hardcoded. Before going to
    production, move SECRET_KEY and the database URL into environment
    variables instead of committing them to source control.
    """
    SECRET_KEY = os.environ.get("KISAN_ROUTE_SECRET_KEY", "kisan-route-dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "KISAN_ROUTE_DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'kisanroute.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB upload limit
