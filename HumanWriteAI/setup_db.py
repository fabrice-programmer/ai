"""Database setup script: create all tables and initialize Alembic migrations."""

import os
import sys

os.environ["FLASK_ENV"] = "development"

# Ensure we can import from the project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app


def create_tables():
    """Create all database tables from SQLAlchemy models."""
    with app.app_context():
        from backend.extensions import db
        from sqlalchemy import inspect

        db.create_all()

        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"✓ Tables created: {tables}")
        return tables


def init_migrations():
    """Initialize Alembic migrations directory if not already present."""
    from flask_migrate import migrate as flask_migrate

    with app.app_context():
        from backend.extensions import migrate
        from flask_migrate import init, migrate, upgrade

        migrations_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "migrations"
        )

        if not os.path.exists(migrations_dir):
            print("→ Initializing Alembic migrations...")
            init()
            print("✓ Migrations directory created")
        else:
            print("→ Migrations directory already exists")

        print("→ Creating migration script...")
        migrate(message="Initial migration: users, documents, analyses")
        print("✓ Migration script created")

        print("→ Applying migration...")
        upgrade()
        print("✓ Database upgraded to latest migration")


if __name__ == "__main__":
    create_tables()
    print("Done!")