"""Download route — generate and download a .docx file from processed text."""

import logging
import tempfile
from pathlib import Path

from flask import Blueprint, jsonify, request, send_file

from backend.services.docx_generator import generate_docx
from backend.utils.error_handlers import AppError

logger = logging.getLogger(__name__)

download_bp = Blueprint("download", __name__, url_prefix="/api/download")


@download_bp.route("/docx", methods=["POST"])
def download_docx():
    """Generate a .docx file from provided processed text and return it.

    Request JSON body::

        {
            "text": "... processed text with markdown headings ...",
            "title": "Optional Document Title"
        }

    The service preserves headings (# ## ###), paragraphs, and
    reference sections in the generated .docx file.

    Returns
    -------
    Response
        The .docx file as an attachment download, or a JSON error.

    Status codes
    ------------
    200 — File ready for download (content-type: application/vnd.openxmlformats-officedocument.wordprocessingml.document)
    400 — Missing or invalid request body
    500 — Server-side generation failure
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    text = data.get("text")
    if not text or not text.strip():
        return jsonify({"error": "The 'text' field is required and must be non-empty"}), 400

    title = data.get("title")

    tmp_path = None
    try:
        # Generate to a temporary file so we can send it as an attachment
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            tmp_path = tmp.name

        saved_path = generate_docx(
            text=text,
            output_path=tmp_path,
            title=title,
        )

        filename = f"{title or 'document'}.docx"
        if not filename.lower().endswith(".docx"):
            filename += ".docx"

        return send_file(
            saved_path,
            mimetype=(
                "application/vnd.openxmlformats-officedocument"
                ".wordprocessingml.document"
            ),
            as_attachment=True,
            download_name=filename,
        )
    except AppError as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception:
        logger.exception("Failed to generate .docx file")
        return jsonify({"error": "An unexpected error occurred while generating the document"}), 500
    finally:
        # Clean up the temp file after the response is sent
        if tmp_path:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except Exception:
                logger.warning("Could not delete temp file %s", tmp_path)