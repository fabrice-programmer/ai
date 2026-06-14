"""Document routes — upload, list, retrieve, and delete documents."""

import logging
from flask import Blueprint, current_app, jsonify, request
from backend.services.document_service import (
    upload_document,
    get_document,
    get_user_documents,
    delete_document,
)
from backend.utils.error_handlers import AppError

logger = logging.getLogger(__name__)

documents_bp = Blueprint("documents", __name__, url_prefix="/api/documents")


@documents_bp.route("/upload", methods=["POST"])
def upload():
    """Upload a .docx file, extract text, and persist to the database.

    Expects multipart/form-data with:
      - file:     the uploaded .docx file
      - user_id:  (int) ID of the uploading user (simple auth stub)

    Server-side validation includes:
      - File presence and valid filename
      - Allowed extension (.docx only)
      - File size (configurable via MAX_FILE_SIZE_MB)
    """
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files["file"]
    user_id = request.form.get("user_id", type=int)

    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    cfg = current_app.config
    try:
        doc = upload_document(
            user_id=user_id,
            file=file,
            upload_folder=cfg["UPLOAD_FOLDER"],
            allowed_extensions=cfg.get("ALLOWED_EXTENSIONS", {".docx"}),
            max_size_mb=cfg.get("MAX_FILE_SIZE_MB", 10),
            subdir=cfg.get("UPLOAD_SUBDIR", "documents"),
        )
        return jsonify({"message": "Document uploaded", "document": doc.to_dict()}), 201
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
    """List all documents for a given user, newest first."""
    docs = get_user_documents(user_id)
    return jsonify({"documents": [d.to_dict() for d in docs]})


@documents_bp.route("/<int:doc_id>", methods=["DELETE"])
def remove_document(doc_id: int):
    """Delete a document and its stored file."""
    try:
        delete_document(doc_id)
        return jsonify({"message": "Document deleted"}), 200
    except AppError as e:
        return jsonify({"error": e.message}), e.status_code