"""Analysis routes — analyse documents and raw text."""

import logging
from flask import Blueprint, jsonify, request
from backend.services.analysis_service import (
    analyze_document,
    analyze_text,
    get_analysis,
    get_document_analyses,
)
from backend.utils.error_handlers import AppError

logger = logging.getLogger(__name__)

analysis_bp = Blueprint("analysis", __name__, url_prefix="/api")


@analysis_bp.route("/analyze/document/<int:document_id>", methods=["POST"])
def analyze_document_paragraphs(document_id: int):
    """Analyse a stored document using paragraph-level AI detection.

    Splits the document into paragraphs, sends each paragraph through
    the AI model, and returns overall AI/human scores and confidence
    alongside the per-paragraph breakdown. Results are persisted to the
    database.

    Returns:
        JSON with overall and per-paragraph analysis results.
    """
    try:
        analysis = analyze_document(document_id)
        return jsonify({
            "message": "Analysis complete",
            "analysis": analysis.to_dict(),
        }), 201
    except AppError as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception:
        logger.exception("Document analysis failed")
        return jsonify({"error": "An unexpected error occurred"}), 500


@analysis_bp.route("/predict", methods=["POST"])
def predict():
    """Predict whether the provided text is AI-generated (ad-hoc)."""
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")

    if not text:
        return jsonify({"error": "text field is required"}), 400

    try:
        result = analyze_text(text)
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503
    except Exception:
        logger.exception("Prediction failed")
        return jsonify({"error": "An unexpected error occurred"}), 500


@analysis_bp.route(
    "/documents/<int:document_id>/analyse",
    methods=["POST"],
)
def analyse_document(document_id: int):
    """Analyse a stored document and persist the result."""
    try:
        analysis = analyze_document(document_id)
        return jsonify({
            "message": "Analysis complete",
            "analysis": analysis.to_dict(),
        }), 201
    except AppError as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception:
        logger.exception("Document analysis failed")
        return jsonify({"error": "An unexpected error occurred"}), 500


@analysis_bp.route("/analyses/<int:analysis_id>", methods=["GET"])
def get_analysis_by_id(analysis_id: int):
    """Retrieve a single analysis by ID."""
    try:
        analysis = get_analysis(analysis_id)
        return jsonify({"analysis": analysis.to_dict()})
    except AppError as e:
        return jsonify({"error": e.message}), e.status_code


@analysis_bp.route(
    "/documents/<int:document_id>/analyses",
    methods=["GET"],
)
def list_document_analyses(document_id: int):
    """List all analyses for a document."""
    analyses = get_document_analyses(document_id)
    return jsonify({"analyses": [a.to_dict() for a in analyses]})