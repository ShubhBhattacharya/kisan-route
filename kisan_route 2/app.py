import os
import sys

# Ensure Vercel finds all relative imports properly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, session, request, render_template, make_response
from config import Config
from extensions import db
from translations.strings import LANGUAGES, translate


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

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
        else:
            tmp_db = "/tmp/kisanroute.db"
            app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{tmp_db}"
            src_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kisanroute.db")
            if not os.path.exists(tmp_db) and os.path.exists(src_db):
                import shutil
                try:
                    shutil.copyfile(src_db, tmp_db)
                    print("Copied initial database to /tmp")
                except Exception as e:
                    print("Database copy to /tmp skipped:", e)

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

    @app.context_processor
    def inject_globals():
        lang = session.get("lang", "en")

        def t(key):
            return translate(lang, key)

        from utils.weather import get_agri_weather
        from utils.news import get_agri_news
        return dict(
            t=t,
            current_lang=lang,
            languages=LANGUAGES,
            agri_weather=get_agri_weather(),
            agri_news=get_agri_news()
        )

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

        # Check bypass via URL query param e.g. ?bypass=123456
        bypass_key = request.args.get("bypass", "")
        if bypass_key and is_bypass_authorized(bypass_key):
            session["maintenance_bypass"] = True

        if session.get("maintenance_bypass"):
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
            print("Database initialization/seed handled:", e)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)