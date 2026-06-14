"""Authentication routes — register & login."""

import logging
from flask import Blueprint, jsonify, request
from backend.models.schemas import register_schema, login_schema
from backend.services.auth_service import register_user, authenticate_user, get_user_by_id
from backend.utils.error_handlers import AppError

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/register", methods=["POST"])
def register():
    """Register a new user."""
    data = request.get_json(silent=True) or {}

    # Validate with marshmallow
    errors = register_schema.validate(data)
    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400

    try:
        user = register_user(
            username=data["username"],
            email=data["email"],
            password=data["password"],
        )
        return jsonify({"message": "User registered", "user": user.to_dict()}), 201
    except AppError as e:
        return jsonify({"error": e.message}), e.status_code


@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate a user and return user info."""
    data = request.get_json(silent=True) or {}

    errors = login_schema.validate(data)
    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400

    try:
        user = authenticate_user(data["username"], data["password"])
        return jsonify({"message": "Login successful", "user": user.to_dict()})
    except AppError as e:
        return jsonify({"error": e.message}), e.status_code


@auth_bp.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id: int):
    """Get user details by ID."""
    try:
        user = get_user_by_id(user_id)
        return jsonify({"user": user.to_dict()})
    except AppError as e:
        return jsonify({"error": e.message}), e.status_code