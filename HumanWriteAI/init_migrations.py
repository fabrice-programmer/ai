"""Initialize Alembic migrations directory and create the initial migration."""

import os
import sys

os.environ["FLASK_ENV"] = "development"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from flask_migrate import init, migrate, stamp, upgrade


def setup():
    with app.app_context():
        # Only init if migrations directory doesn't exist
        migrations_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "migrations"
        )
        if not os.path.exists(migrations_dir):
            print(">> Initializing Alembic ...")
            init(directory=migrations_dir)
            print(">> Alembic initialized")
        else:
            print(">> Alembic already initialized")

        # Create initial migration
        print(">> Creating initial migration ...")
        migrate(directory=migrations_dir, message="Initial full schema")
        print(">> Migration script created")

        # Apply the migration
        print(">> Applying migration ...")
        upgrade(directory=migrations_dir)
        print(">> Database upgraded to latest revision")


if __name__ == "__main__":
    setup()