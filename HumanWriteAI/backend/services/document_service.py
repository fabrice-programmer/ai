"""Document service — handles file upload, text extraction, and DB persistence."""

import logging
import os
from werkzeug.datastructures import FileStorage
from backend.extensions import db
from backend.models.document import Document
from backend.utils.error_handlers import AppError

logger = logging.getLogger(__name__)

# Supported file extensions for text extraction
SUPPORTED_EXTENSIONS = {".txt", ".docx", ".pdf"}


def upload_document(
    user_id: int,
    file: FileStorage,
    upload_folder: str,
) -> Document:
    """Validate, save, and create a Document record."""
    validate_file(file)
    text = extract_text_from_file(file)

    # Save file to disk
    filename = file.filename or "unknown"
    save_path = os.path.join(upload_folder, filename)
    file.save(save_path)

    doc = Document(
        user_id=user_id,
        filename=filename,
        extracted_text=text,
        text_length=len(text) if text else 0,
        status="completed",
    )
    db.session.add(doc)
    db.session.commit()

    logger.info("Document %d uploaded by user %d", doc.id, user_id)
    return doc


def get_document(doc_id: int) -> Document:
    """Retrieve a document by ID."""
    doc = db.session.get(Document, doc_id)
    if not doc:
        raise AppError("Document not found", 404)
    return doc


def get_user_documents(user_id: int) -> list[Document]:
    """List all documents belonging to a user."""
    return Document.query.filter_by(user_id=user_id).order_by(
        Document.upload_date.desc()
    ).all()


def extract_text_from_file(file: FileStorage) -> str:
    """Extract text content from an uploaded file.

    Delegates to format-specific extractors.
    """
    filename = file.filename or "unknown"
    ext = _get_extension(filename)

    logger.info("Extracting text from '%s'", filename)

    # Seek to start in case the file stream was already read
    file.seek(0)

    if ext == ".txt":
        return _extract_txt(file)
    elif ext == ".docx":
        return _extract_docx(file)
    elif ext == ".pdf":
        return _extract_pdf(file)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def validate_file(file: FileStorage) -> None:
    """Validate that the uploaded file is acceptable."""
    if not file or not file.filename:
        raise ValueError("No file provided")

    ext = _get_extension(file.filename)
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"File type '{ext}' is not supported. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )


# ── Internal helpers ──────────────────────────────────────────────


def _get_extension(filename: str) -> str:
    _, ext = os.path.splitext(filename)
    return ext.lower()


def _extract_txt(file: FileStorage) -> str:
    return file.read().decode("utf-8", errors="replace")


def _extract_docx(file: FileStorage) -> str:
    try:
        from docx import Document as DocxDocument

        doc = DocxDocument(file)
        return "\n".join(p.text for p in doc.paragraphs)
    except ImportError:
        logger.warning("python-docx not installed; falling back to raw read")
        return file.read().decode("utf-8", errors="replace")


def _extract_pdf(file: FileStorage) -> str:
    # Placeholder: integrate PyMuPDF / pdfminer when needed
    raise NotImplementedError("PDF extraction is not yet implemented")