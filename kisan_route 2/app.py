import os
import sys

# Ensure Vercel finds all relative imports properly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, session
from config import Config
from extensions import db
from translations.strings import LANGUAGES, translate


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Vercel Serverless environment compatibility
    if os.environ.get("VERCEL"):
        # Serverless environment me sirf /tmp writable hota hai
        app.config["UPLOAD_FOLDER"] = "/tmp/uploads"
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:////tmp/kisanroute.db"

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

        return dict(t=t, current_lang=lang, languages=LANGUAGES)

    # Database create ko safe try-except me rakhein
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            print("Database creation handled:", e)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)