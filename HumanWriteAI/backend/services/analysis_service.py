"""Analysis service — runs AI detection and persists results to the database."""

import logging
import re
from typing import Any
from backend.extensions import db
from backend.models.analysis import Analysis
from backend.utils.error_handlers import AppError

logger = logging.getLogger(__name__)


def _extract_paragraphs(text: str) -> list[str]:
    """Split document text into non-empty paragraphs.

    Paragraphs are separated by one or more blank lines (two or more
    newline characters) or by common section-break patterns.

    Returns:
        A list of paragraph strings, stripped of leading/trailing whitespace.
    """
    # Split on two or more newlines (with optional whitespace between them)
    raw = re.split(r"\n\s*\n", text)
    paragraphs = [p.strip() for p in raw if p.strip()]
    # Filter out any paragraph that is just whitespace/punctuation only
    paragraphs = [p for p in paragraphs if re.search(r"[a-zA-Z0-9]{3,}", p)]
    return paragraphs if paragraphs else [text.strip()]


def _aggregate_paragraph_results(
    paragraph_results: list[dict[str, Any]],
) -> dict[str, float]:
    """Aggregate per-paragraph scores into overall document-level scores.

    Args:
        paragraph_results: List of dicts each containing 'ai_score',
                           'human_score', and 'confidence'.

    Returns:
        A dict with 'ai_score', 'human_score', and 'confidence'.
    """
    if not paragraph_results:
        return {"ai_score": 0.5, "human_score": 0.5, "confidence": 0.0}

    # Use mean (simple average) for aggregation
    n = len(paragraph_results)
    ai_total = sum(p["ai_score"] for p in paragraph_results)
    human_total = sum(p["human_score"] for p in paragraph_results)
    conf_total = sum(p["confidence"] for p in paragraph_results)

    return {
        "ai_score": round(ai_total / n, 6),
        "human_score": round(human_total / n, 6),
        "confidence": round(conf_total / n, 6),
    }


def analyze_document(document_id: int) -> Analysis:
    """Run AI prediction on a document's extracted text and store the result.

    The document text is split into paragraphs. Each paragraph is analysed
    individually, and the per-paragraph results are aggregated into overall
    AI score, human score, and confidence.

    The individual paragraph results are stored in the database alongside
    the aggregate scores.

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

    # Split into paragraphs and analyse each one
    paragraphs = _extract_paragraphs(text)
    logger.info(
        "Document %d: split into %d paragraphs for analysis",
        document_id, len(paragraphs),
    )

    paragraph_results: list[dict[str, Any]] = []
    for idx, para in enumerate(paragraphs):
        para_result = _run_prediction(para)
        paragraph_results.append(
            {
                "paragraph_index": idx,
                "text_preview": para[:120],
                "ai_score": para_result["ai_score"],
                "human_score": para_result["human_score"],
                "confidence": para_result["confidence"],
            }
        )

    # Aggregate into overall scores
    aggregate = _aggregate_paragraph_results(paragraph_results)

    analysis = Analysis(
        document_id=doc.id,
        ai_score=aggregate["ai_score"],
        human_score=aggregate["human_score"],
        confidence=aggregate["confidence"],
        paragraphs_data=paragraph_results,
    )
    db.session.add(analysis)
    doc.status = "completed"
    db.session.commit()

    logger.info(
        "Analysis %d created for document %d (%d paragraphs)",
        analysis.id, document_id, len(paragraph_results),
    )
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

    The AI engine's predict_text() returns keys:
        ai_probability, human_probability, classification, confidence.

    This helper normalises them to: ai_score, human_score, confidence.

    Returns:
        A dict with keys: ai_score, human_score, confidence.
    """
    try:
        from ai_engine.inference.predict import predict_text

        result = predict_text(text)
    except ImportError as exc:
        logger.error("AI engine not available: %s", exc)
        raise RuntimeError("AI analysis engine is not available") from exc

    return {
        "ai_score": result.get("ai_probability", 0.5),
        "human_score": result.get("human_probability", 0.5),
        "confidence": result.get("confidence", 0.0),
    }
