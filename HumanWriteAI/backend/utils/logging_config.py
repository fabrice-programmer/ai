import logging
import sys
from flask import Flask


def configure_logging(app: Flask) -> None:
    """Configure structured logging for the application.

    Sets up a consistent log format and applies the configured log level.
    """
    log_level = app.config.get("LOG_LEVEL", logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    # Attach handler to the root logger if none exist
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        root_logger.addHandler(handler)
        root_logger.setLevel(log_level)

    # Set Flask's own logger level
    app.logger.setLevel(log_level)
    app.logger.info("Logging configured at %s level", logging.getLevelName(log_level))