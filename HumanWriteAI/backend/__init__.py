import os
from pathlib import Path
from flask import Flask, send_from_directory
from flask_cors import CORS
from backend.extensions import db, migrate
from backend.config import config_map
from backend.utils.logging_config import configure_logging
from backend.utils.error_handlers import register_error_handlers


# Frontend directory (two levels up from this file → HumanWriteAI/frontend)
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


def create_app(config_name: str | None = None) -> Flask:
    """Application factory for HumanWriteAI.

    Args:
        config_name: One of 'development', 'production', 'testing'.
                     Defaults to the FLASK_ENV env var or 'development'.

    Returns:
        A fully configured Flask application instance.
    """
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")

    app = Flask(
        __name__,
        static_folder=str(FRONTEND_DIR),
        static_url_path="",
    )

    # Load configuration
    app.config.from_object(config_map.get(config_name, config_map["development"]))

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app)

    # Register blueprints
    _register_blueprints(app)

    # Error handlers
    register_error_handlers(app)

    # Logging
    configure_logging(app)

    # Serve the frontend index.html at the root
    @app.route("/")
    def home():
        return send_from_directory(FRONTEND_DIR, "index.html")

    return app


def _register_blueprints(app: Flask) -> None:
    """Import and register all application blueprints."""
    from backend.routes.auth import auth_bp
    from backend.routes.documents import documents_bp
    from backend.routes.analysis import analysis_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(analysis_bp)