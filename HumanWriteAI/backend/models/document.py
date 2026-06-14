"""Document model for HumanWriteAI."""

from datetime import datetime, timezone

from backend.extensions import db


class Document(db.Model):
    """Uploaded document with extracted text and processing status."""

    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename = db.Column(db.String(300), nullable=False)
    extracted_text = db.Column(db.Text, nullable=True)
    text_length = db.Column(db.Integer, nullable=True)
    upload_date = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    status = db.Column(
        db.String(20),
        nullable=False,
        default="pending",
        index=True,
    )  # pending | processing | completed | failed

    # Absolute path to the stored file on disk
    stored_path = db.Column(db.String(500), nullable=True)

    # ── Relationships ──────────────────────────────────────────
    user = db.relationship("User", back_populates="documents")
    analyses = db.relationship(
        "Analysis",
        back_populates="document",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    # ── Serialisation ──────────────────────────────────────────
    def to_dict(self) -> dict:
        """Serialize document to a dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "filename": self.filename,
            "extracted_text": self.extracted_text,
            "text_length": self.text_length,
            "upload_date": self.upload_date.isoformat() if self.upload_date else None,
            "status": self.status,
        }

    def __repr__(self) -> str:
        return f"<Document {self.id}: {self.filename} ({self.status})>"