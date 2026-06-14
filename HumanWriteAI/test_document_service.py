"""Test the document service upload pipeline: validate -> extract -> persist -> store."""

import io
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["FLASK_ENV"] = "development"

from app import app
from backend.extensions import db
from backend.models.document import Document
from backend.services.document_service import (
    upload_document,
    get_document,
    delete_document,
    validate_file,
    extract_text_from_file,
)
from backend.utils.error_handlers import AppError
from werkzeug.datastructures import FileStorage


def make_docx_bytes(text: str = "Hello, this is a test document.") -> bytes:
    """Create a minimal .docx file in memory using python-docx."""
    from docx import Document as DocxDocument

    doc = DocxDocument()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()


def make_filestorage(
    content: bytes, filename: str = "test.docx",
) -> FileStorage:
    return FileStorage(
        stream=io.BytesIO(content),
        filename=filename,
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


def test_validate_file():
    """Test all validation scenarios."""
    print("--- validate_file tests ---")

    # 1. No file
    try:
        validate_file(None, {".docx"}, 10)
        print("FAIL: should have raised for None file")
    except AppError as e:
        assert "No file" in e.message
        print("  [OK] No file rejected")

    # 2. Empty filename
    try:
        validate_file(make_filestorage(b"hi", ""), {".docx"}, 10)
        print("FAIL: should have raised for empty filename")
    except AppError as e:
        assert "valid filename" in e.message
        print("  [OK] Empty filename rejected")

    # 3. Wrong extension
    try:
        validate_file(make_filestorage(b"hi", "test.pdf"), {".docx"}, 10)
        print("FAIL: should have raised for .pdf")
    except AppError as e:
        assert "not supported" in e.message
        print("  [OK] Wrong extension rejected")

    # 4. Correct extension, small file
    try:
        validate_file(make_filestorage(b"some content", "good.docx"), {".docx"}, 10)
        print("  [OK] Valid file passes")
    except AppError as e:
        print(f"FAIL: valid file should pass: {e.message}")

    # 5. File exceeds size limit
    try:
        big_content = b"x" * (5 * 1024 * 1024 + 1)  # just over 5 MB
        validate_file(make_filestorage(big_content, "big.docx",), {".docx"}, 5)
        print("FAIL: should have raised for oversized file")
    except AppError as e:
        assert "exceeds" in e.message
        print("  [OK] Oversized file rejected")

    print("[PASS] All validation tests passed\n")


def test_extract_text():
    """Test text extraction from a .docx file."""
    print("--- extract_text_from_file tests ---")

    content = "This is paragraph one.\nThis is paragraph two."
    docx_bytes = make_docx_bytes(content)
    file = make_filestorage(docx_bytes, "sample.docx")

    extracted = extract_text_from_file(file)
    print(f"  Extracted text: {repr(extracted)}")

    assert "paragraph one" in extracted
    assert "paragraph two" in extracted
    print("[PASS] Text extraction works correctly\n")


def test_upload_pipeline():
    """Test the full upload pipeline end-to-end."""
    print("--- Full upload pipeline test ---")

    with app.app_context():
        # Create a test user first
        from backend.models.user import User

        user = User.query.filter_by(email="test@example.com").first()
        if not user:
            user = User(username="testuser", email="test@example.com")
            user.password = "password"
            db.session.add(user)
            db.session.commit()
            print("  Created test user")

        cfg = app.config

        # Upload a valid .docx
        docx_bytes = make_docx_bytes("Professional document content for testing.")
        file = make_filestorage(docx_bytes, "my_report.docx")

        doc = upload_document(
            user_id=user.id,
            file=file,
            upload_folder=cfg["UPLOAD_FOLDER"],
            allowed_extensions=cfg.get("ALLOWED_EXTENSIONS", {".docx"}),
            max_size_mb=cfg.get("MAX_FILE_SIZE_MB", 10),
            subdir=cfg.get("UPLOAD_SUBDIR", "documents"),
        )

        print(f"  Created document ID={doc.id}")
        print(f"  Filename: {doc.filename}")
        print(f"  Text length: {doc.text_length}")
        print(f"  Status: {doc.status}")
        print(f"  Stored path: {doc.stored_path}")

        assert doc.id > 0
        assert doc.filename == "my_report.docx"
        assert doc.text_length > 0
        assert doc.status == "completed"
        assert doc.stored_path is not None
        assert os.path.isfile(doc.stored_path), "File not found on disk!"

        # Verify it's retrievable
        fetched = get_document(doc.id)
        assert fetched.id == doc.id
        print("  [OK] Document retrievable from DB")

        # Verify file content on disk
        with open(doc.stored_path, "rb") as f:
            disk_content = f.read()
        assert len(disk_content) > 0
        print(f"  [OK] File on disk ({len(disk_content)} bytes)")

        # Cleanup: delete the document
        file_path = doc.stored_path
        delete_document(doc.id)

        # Verify DB record is gone
        assert not db.session.get(Document, doc.id)
        print("  [OK] DB record deleted")

        # Verify file is gone
        assert not os.path.isfile(file_path), "File should have been deleted!"
        print("  [OK] File removed from disk")

        print("[PASS] Full pipeline test passed\n")


if __name__ == "__main__":
    print("=" * 50)
    print("Document Service Tests")
    print("=" * 50)

    test_validate_file()
    test_extract_text()
    test_upload_pipeline()

    print("=" * 50)
    print("ALL TESTS PASSED")
    print("=" * 50)