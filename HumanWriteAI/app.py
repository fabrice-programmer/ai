"""
HumanWriteAI — Flask application entry point.

Usage:
    flask run
    python app.py
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env before creating the app
load_dotenv()

from backend import create_app  # noqa: E402 (import after dotenv)

app = create_app(os.getenv("FLASK_ENV", "development"))

if __name__ == "__main__":
    app.run(debug=app.config.get("DEBUG", True))