"""Authentication service — handles registration and login."""

import logging
from backend.extensions import db
from backend.models.user import User
from backend.utils.error_handlers import AppError

logger = logging.getLogger(__name__)


def register_user(username: str, email: str, password: str) -> User:
    """Register a new user after validation."""
    if User.query.filter_by(username=username).first():
        raise AppError("Username already exists", 409)

    if User.query.filter_by(email=email).first():
        raise AppError("Email already registered", 409)

    user = User(
        username=username,
        email=email,
    )
    user.password = password  # triggers the setter → hashes

    db.session.add(user)
    db.session.commit()
    logger.info("User '%s' registered successfully", username)
    return user


def authenticate_user(username: str, password: str) -> User:
    """Authenticate a user by username and password."""
    user = User.query.filter_by(username=username).first()
    if not user or not user.verify_password(password):
        raise AppError("Invalid credentials", 401)
    return user


def get_user_by_id(user_id: int) -> User:
    """Retrieve a user by primary key."""
    user = db.session.get(User, user_id)
    if not user:
        raise AppError("User not found", 404)
    return user