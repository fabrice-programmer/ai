"""Analysis model for HumanWriteAI."""

from datetime import datetime, timezone

from backend.extensions import db


class Analysis(db.Model):
    """AI-content detection analysis result for a document."""

    __tablename__ = "analyses"

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(
        db.Integer,
        db.ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ai_score = db.Column(db.Float, nullable=False)
    human_score = db.Column(db.Float, nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ──────────────────────────────────────────
    document = db.relationship("Document", back_populates="analyses")

    # ── Serialisation ──────────────────────────────────────────
    def to_dict(self) -> dict:
        """Serialize analysis to a dictionary."""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "ai_score": self.ai_score,
            "human_score": self.human_score,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return (
            f"<Analysis {self.id}: "
            f"AI={self.ai_score:.3f} Human={self.human_score:.3f} "
            f"Conf={self.confidence:.3f}>"
        )