import os

from flask import Flask, session

from config import Config
from extensions import db
from translations.strings import LANGUAGES, translate


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

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

    with app.app_context():
        db.create_all()

    return app


app = create_app()

if __name__ == "__main__":
    # debug=True gives auto-reload + in-browser tracebacks while you build.
    # Turn it off before showing this to judges on a shared network.
    app.run(debug=True, host="127.0.0.1", port=5000)
