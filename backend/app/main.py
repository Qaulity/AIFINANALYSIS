"""Main Flask application entry point."""
from flask import Flask
from flask_cors import CORS
from loguru import logger
import sys

from .config import get_settings
from .api import api_bp


def create_app() -> Flask:
    """Create and configure the Flask application."""
    settings = get_settings()

    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="DEBUG" if settings.DEBUG else "INFO"
    )

    # Create Flask app
    app = Flask(__name__)
    app.config["DEBUG"] = settings.DEBUG

    # Enable CORS for React frontend
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:3000", "http://localhost:5173"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })

    # Register API blueprint
    app.register_blueprint(api_bp)

    # Root endpoint
    @app.route("/")
    def index():
        return {
            "name": settings.APP_NAME,
            "version": "1.0.0",
            "docs": "/api/docs"
        }

    logger.info(f"Application '{settings.APP_NAME}' initialized")
    return app


# For running with `flask run` or `python -m app.main`
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
