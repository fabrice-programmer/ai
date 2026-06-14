"""User model for HumanWriteAI."""

from datetime import datetime, timezone

from backend.extensions import db


class User(db.Model):
    """Application user model."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ──────────────────────────────────────────
    documents = db.relationship(
        "Document",
        back_populates="user",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    # ── Convenience ────────────────────────────────────────────
    @property
    def password(self):
        """Prevent direct access to password_hash."""
        raise AttributeError("password is not a readable attribute")

    @password.setter
    def password(self, plaintext: str) -> None:
        """Hash and store the password."""
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(plaintext)

    def verify_password(self, plaintext: str) -> bool:
        """Check the supplied password against the stored hash."""
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, plaintext)

    # ── Serialisation ──────────────────────────────────────────
    def to_dict(self) -> dict:
        """Serialize user to a safe dictionary (excludes password)."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.email})>"