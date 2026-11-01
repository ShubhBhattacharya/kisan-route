import os
import sys

# Ensure Vercel finds all relative imports properly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, session, request, render_template, make_response
from config import Config
from extensions import db
from translations.strings import LANGUAGES, translate


def create_app(config_override=None):
    app = Flask(__name__)
    app.config.from_object(Config)

    if config_override:
        app.config.update(config_override)

    if os.environ.get("TEST_DATABASE_URL") and (not config_override or "SQLALCHEMY_DATABASE_URI" not in config_override):
        app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["TEST_DATABASE_URL"]

    # Industry-Grade Cookie & Session Hardening
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    if not app.debug or os.environ.get("VERCEL"):
        app.config["SESSION_COOKIE_SECURE"] = True

    # Vercel Serverless environment compatibility
    if os.environ.get("VERCEL"):
        app.config["UPLOAD_FOLDER"] = "/tmp/uploads"
        remote_db = (
            os.environ.get("SUPABASE_DB_URL")
            or os.environ.get("KISAN_ROUTE_DATABASE_URL")
            or os.environ.get("DATABASE_URL")
        )
        if remote_db:
            if remote_db.startswith("postgres://"):
                remote_db = remote_db.replace("postgres://", "postgresql://", 1)
            app.config["SQLALCHEMY_DATABASE_URI"] = remote_db

    db.init_app(app)

    # Safe folder creation (crash hone se rokega)
    try:
        os.makedirs(app.config.get("UPLOAD_FOLDER", "/tmp"), exist_ok=True)
    except Exception as e:
        print("Upload folder setup skipped:", e)

    # --- Blueprints: one per role, plus a shared "main" blueprint ---
    from blueprints.main import main_bp
    from blueprints.farmer import farmer_bp
    from blueprints.cluster import cluster_bp
    from blueprints.customer import customer_bp
    from blueprints.driver import driver_bp
    from blueprints.wholesaler import wholesaler_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(farmer_bp, url_prefix="/farmer")
    app.register_blueprint(cluster_bp, url_prefix="/cluster")
    app.register_blueprint(customer_bp, url_prefix="/customer")
    app.register_blueprint(driver_bp, url_prefix="/driver")
    app.register_blueprint(wholesaler_bp, url_prefix="/wholesaler")

    # Meta WhatsApp Cloud API & Kisan Mitra Assistant Blueprint
    from routes.whatsapp_webhook import whatsapp_bp
    app.register_blueprint(whatsapp_bp)

    # Free Self-Hosted Baileys WhatsApp Bridge Blueprint
    from routes.local_whatsapp import local_whatsapp_bp
    app.register_blueprint(local_whatsapp_bp)

    # Protected Kisan Route Guardian AI Admin Control Center & Background Engine
    from blueprints.guardian import guardian_bp
    app.register_blueprint(guardian_bp)

    # Module 23: Private Owner-Only AI Control, Backend Operations & Access Management
    from blueprints.owner import owner_bp
    app.register_blueprint(owner_bp)

    @app.context_processor
    def inject_globals():
        lang = session.get("lang", "en")

        def t(key):
            return translate(lang, key)

        from utils.weather import get_agri_weather
        from utils.news import get_agri_news
        from utils.bids import get_all_bids
        return dict(
            t=t,
            current_lang=lang,
            languages=LANGUAGES,
            agri_weather=get_agri_weather(),
            agri_news=get_agri_news(),
            live_bids=[b for b in get_all_bids() if "declined" not in str(b.get("status", "")).lower() and "rejected" not in str(b.get("status", "")).lower()]
        )

    # Production configuration guard — deferred to first request so the module-level
    # 'app' symbol is always a valid WSGI callable (required by Vercel's Python runtime).
    # Raises 500 on the very first request if essential env vars are absent, making
    # misconfiguration immediately visible without blocking Vercel's build-time import.
    _vercel_config_checked = [False]

    @app.before_request
    def check_vercel_production_config():
        if _vercel_config_checked[0]:
            return None
        _vercel_config_checked[0] = True
        if os.environ.get("VERCEL"):
            if not app.config.get("SECRET_KEY"):
                raise RuntimeError(
                    "KISAN_ROUTE_SECRET_KEY or SECRET_KEY must be configured in production."
                )
            if not (
                os.environ.get("SUPABASE_DB_URL")
                or os.environ.get("KISAN_ROUTE_DATABASE_URL")
                or os.environ.get("DATABASE_URL")
            ):
                raise RuntimeError(
                    "Persistent PostgreSQL DATABASE_URL is required in production; refusing ephemeral SQLite."
                )
        return None

    # Maintenance Mode Interceptor (Returns 503 if active, allows bypass for admin)
    @app.before_request
    def check_maintenance():
        # Allow static files and PWA service worker / icons
        if request.path.startswith("/static") or request.path in ("/manifest.json", "/sw.js", "/favicon.ico", "/icon-192.png", "/icon-512.png"):
            return None

        # Allow maintenance control routes
        if request.path.startswith("/maintenance"):
            return None

        from utils.maintenance import is_maintenance_mode, is_bypass_authorized

        # Maintenance bypass must be established through the authenticated
        # maintenance control flow, never through a URL query parameter.
        if session.get("maintenance_bypass") and session.get("maintenance_auth_method") == "owner_session":
            return None

        # If maintenance mode is active, return 503 with maintenance template
        if is_maintenance_mode():
            res = make_response(render_template("maintenance.html"), 503)
            res.headers["Retry-After"] = "300"
            return res

    # Custom Branded Error Handlers
    @app.errorhandler(404)
    def handle_404(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def handle_500(e):
        return render_template("errors/500.html"), 500

    # First-class Security Headers, Caching & Browser Hardening
    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(self), camera=(self), microphone=(self)"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self' https: data: blob: 'unsafe-inline' 'unsafe-eval'; "
            "img-src 'self' https: data: blob:; "
            "script-src 'self' https: 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' https: 'unsafe-inline'; "
            "font-src 'self' https: data:;"
        )
        # Static asset aggressive caching for minimum server load
        if request.path.startswith("/static"):
            response.headers["Cache-Control"] = "public, max-age=86400, stale-while-revalidate=3600"
        if not app.debug or os.environ.get("VERCEL"):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        return response

    # Database create and auto-seed demo accounts
    with app.app_context():
        try:
            db.create_all()
            from models import User
            from werkzeug.security import generate_password_hash

            demo_accounts = []
            if os.environ.get("ENABLE_DEMO_ACCOUNTS", "").lower() in ("1", "true", "yes") and not os.environ.get("VERCEL"):
                demo_accounts = [
                    ("customer", "Demo Customer", "9876543210", "123456"),
                    ("farmer", "Demo Farmer", "9876543210", "123456"),
                    ("driver", "Demo Driver", "9876543210", "123456"),
                    ("wholesaler", "Demo Wholesaler", "9876543210", "123456"),
                    ("cluster", "Demo Cluster Hub", "9876543210", "123456"),
                ]
            for role, name, phone, pwd in demo_accounts:
                if not User.query.filter_by(role=role, phone=phone).first():
                    u = User(
                        role=role,
                        full_name=name,
                        phone=phone,
                        password_hash=generate_password_hash(pwd),
                    )
                    u.set_extra({
                        "address": "Sector 18, Krishi Bhawan",
                        "city": "Noida",
                        "state": "Uttar Pradesh",
                        "pincode": "201301",
                        "crop_type": "Wheat",
                        "profile_complete": True
                    })
                    db.session.add(u)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            if os.environ.get("VERCEL"):
                raise RuntimeError("Production database initialization failed; refusing to start.") from e
            print("Database initialization/seed handled:", e)

    return app


class _LazyApp:
    """Lazy WSGI wrapper — defers Flask app creation until the first request.

    Vercel's Python runtime requires the module-level 'app' symbol to be a valid
    WSGI callable at import time.  This wrapper satisfies that requirement while
    allowing guardian_daemon.py to control Flask initialisation in worker mode
    (after its own PostgreSQL validation has completed).
    """

    def __init__(self):
        self._app = None

    def _get_app(self):
        if self._app is None:
            self._app = create_app()
        return self._app

    def __call__(self, environ, start_response):
        return self._get_app()(environ, start_response)

    def __getattr__(self, name):
        # Delegate attribute access to the real Flask app (e.g. test_client,
        # config, extensions) so test helpers that import app.app work correctly.
        return getattr(self._get_app(), name)


# Module-level WSGI entrypoint.
# Guardian worker sets KISAN_WORKER_MODE=1 before importing this module.
# In that case we still expose a valid (lazy) WSGI object so Vercel or any
# import scanner never sees app=None, but the worker itself will call
# init_worker_app() which directly invokes create_app() with the validated URI.
if os.environ.get("KISAN_WORKER_MODE") == "1":
    # Worker mode — expose a lazy placeholder; guardian_daemon controls real init.
    app = _LazyApp()
else:
    app = create_app()

if __name__ == "__main__":
    concrete = create_app()
    concrete.run(debug=True, host="127.0.0.1", port=5000)
