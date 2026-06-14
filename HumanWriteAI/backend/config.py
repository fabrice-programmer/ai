"""Application configuration — supports development, testing, and production."""

import os
from pathlib import Path

# Base directory of the project (two levels up from this file)
BASE_DIR = Path(__file__).resolve().parent.parent


class BaseConfig:
    """Base configuration with shared settings."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── Database ───────────────────────────────────────────────
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'humanwrite.db'}",
    )
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,  # verify connections before use
        "pool_recycle": 300,    # recycle connections every 5 minutes
    }

    # ── Uploads ────────────────────────────────────────────────
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
    UPLOAD_FOLDER = str(BASE_DIR / "uploads")


class DevelopmentConfig(BaseConfig):
    """Development environment configuration."""

    DEBUG = True
    SQLALCHEMY_ENGINE_OPTIONS = {
        **BaseConfig.SQLALCHEMY_ENGINE_OPTIONS,
        "echo": True,  # log all SQL statements
    }


class ProductionConfig(BaseConfig):
    """Production environment configuration.

    Expects DATABASE_URL to point to a PostgreSQL instance.
    Falls back to SQLite only if no DATABASE_URL is set.
    """

    DEBUG = False

    # Production-grade pool settings for PostgreSQL
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_size": 10,
        "max_overflow": 20,
    }

    @classmethod
    def validate(cls) -> None:
        """Ensure critical production settings are configured."""
        if not cls.SECRET_KEY or cls.SECRET_KEY == "dev-secret":
            raise RuntimeError(
                "SECRET_KEY environment variable must be set to a strong value "
                "in production"
            )


class TestingConfig(BaseConfig):
    """Testing environment configuration."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}