"""Analysis service — runs AI detection and persists results to the database."""

import logging
from typing import Any
from backend.extensions import db
from backend.models.analysis import Analysis
from backend.utils.error_handlers import AppError

logger = logging.getLogger(__name__)


def analyze_document(document_id: int) -> Analysis:
    """Run AI prediction on a document's extracted text and store the result.

    Args:
        document_id: ID of the Document to analyse.

    Returns:
        The newly created Analysis record.
    """
    from backend.models.document import Document

    doc = db.session.get(Document, document_id)
    if not doc:
        raise AppError("Document not found", 404)

    text = doc.extracted_text
    if not text or not text.strip():
        raise AppError("Document has no extractable text to analyse", 400)

    result = _run_prediction(text)

    analysis = Analysis(
        document_id=doc.id,
        ai_score=result["ai_score"],
        human_score=result["human_score"],
        confidence=result["confidence"],
    )
    db.session.add(analysis)
    doc.status = "completed"
    db.session.commit()

    logger.info("Analysis %d created for document %d", analysis.id, document_id)
    return analysis


def get_analysis(analysis_id: int) -> Analysis:
    """Retrieve an analysis by ID."""
    analysis = db.session.get(Analysis, analysis_id)
    if not analysis:
        raise AppError("Analysis not found", 404)
    return analysis


def get_document_analyses(document_id: int) -> list[Analysis]:
    """List all analyses for a given document."""
    return Analysis.query.filter_by(document_id=document_id).order_by(
        Analysis.created_at.desc()
    ).all()


def analyze_text(text: str) -> dict[str, Any]:
    """Run AI prediction on raw text (ad-hoc, no DB persistence).

    Used by the /api/predict endpoint where no document upload is involved.
    """
    if not text or not text.strip():
        raise ValueError("Text input is empty")

    logger.info("Analyzing text of length %d characters", len(text))
    return _run_prediction(text)


# ── Internal helper ───────────────────────────────────────────────


def _run_prediction(text: str) -> dict[str, Any]:
    """Execute the AI engine prediction.

    Returns a dict with keys: ai_score, human_score, confidence.
    """
    try:
        from ai_engine.inference.predict import predict_text

        result = predict_text(text)
    except ImportError as exc:
        logger.error("AI engine not available: %s", exc)
        raise RuntimeError("AI analysis engine is not available") from exc

    # Ensure all expected keys are present
    return {
        "ai_score": result.get("ai_score", 0.5),
        "human_score": result.get("human_score", 0.5),
        "confidence": result.get("confidence", 0.0),
    }