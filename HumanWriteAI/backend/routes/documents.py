"""Document routes — upload, list, and retrieve documents."""

import logging
from flask import Blueprint, current_app, jsonify, request
from backend.services.document_service import (
    upload_document,
    get_document,
    get_user_documents,
)
from backend.utils.error_handlers import AppError

logger = logging.getLogger(__name__)

documents_bp = Blueprint("documents", __name__, url_prefix="/api/documents")


@documents_bp.route("/upload", methods=["POST"])
def upload():
    """Upload a document, extract text, and persist to the database.

    Expects multipart/form-data with:
      - file: the uploaded file
      - user_id: (int) ID of the uploading user (simple auth stub)
    """
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files["file"]
    user_id = request.form.get("user_id", type=int)

    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    try:
        upload_folder = current_app.config["UPLOAD_FOLDER"]
        doc = upload_document(user_id, file, upload_folder)
        return jsonify({"message": "Document uploaded", "document": doc.to_dict()}), 201
    except (ValueError, NotImplementedError) as e:
        return jsonify({"error": str(e)}), 400
    except AppError as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception:
        logger.exception("Unexpected upload error")
        return jsonify({"error": "An unexpected error occurred"}), 500


@documents_bp.route("/<int:doc_id>", methods=["GET"])
def get_doc(doc_id: int):
    """Retrieve a single document by ID."""
    try:
        doc = get_document(doc_id)
        return jsonify({"document": doc.to_dict()})
    except AppError as e:
        return jsonify({"error": e.message}), e.status_code


@documents_bp.route("/user/<int:user_id>", methods=["GET"])
def list_user_documents(user_id: int):
    """List all documents for a given user."""
    docs = get_user_documents(user_id)
    return jsonify({"documents": [d.to_dict() for d in docs]})