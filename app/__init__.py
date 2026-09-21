import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app(config_name=None):
    """Application factory: cria e configura a instância do Flask."""
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    from config import config_by_name

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_by_name[config_name])

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)

    from app.routes.web import web_bp
    from app.routes.api import api_bp

    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    with app.app_context():
        from app import models  # noqa: F401

        db.create_all()

    @app.context_processor
    def inject_globals():
        from datetime import datetime

        return {"ano_atual": datetime.now().year}

    return app
