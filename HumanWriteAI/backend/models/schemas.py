"""Marshmallow schemas for request/response validation.

Used by services and routes to validate incoming data before
it reaches the database layer.
"""

from marshmallow import (
    Schema,
    fields,
    validate,
    validates_schema,
    ValidationError,
)


class UserRegisterSchema(Schema):
    """Validate user registration payload."""

    username = fields.String(
        required=True,
        validate=validate.Length(min=3, max=80),
    )
    email = fields.Email(
        required=True,
        validate=validate.Length(max=150),
    )
    password = fields.String(
        required=True,
        validate=validate.Length(min=8, max=128),
    )


class UserLoginSchema(Schema):
    """Validate login payload."""

    username = fields.String(required=True)
    password = fields.String(required=True)


class DocumentUploadSchema(Schema):
    """Validate document upload metadata (extracted from file)."""

    filename = fields.String(
        required=True,
        validate=validate.Length(max=300),
    )


class AnalysisRequestSchema(Schema):
    """Validate analysis request payload."""

    text = fields.String(
        required=True,
        validate=validate.Length(min=1),
    )


class DocumentResponseSchema(Schema):
    """Shape for document response (excludes raw text)."""

    id = fields.Integer(dump_only=True)
    user_id = fields.Integer(dump_only=True)
    filename = fields.String(dump_only=True)
    text_length = fields.Integer(dump_only=True)
    upload_date = fields.DateTime(dump_only=True)
    status = fields.String(dump_only=True)


class AnalysisResponseSchema(Schema):
    """Shape for analysis response."""

    id = fields.Integer(dump_only=True)
    document_id = fields.Integer(dump_only=True)
    ai_score = fields.Float(dump_only=True)
    human_score = fields.Float(dump_only=True)
    confidence = fields.Float(dump_only=True)
    created_at = fields.DateTime(dump_only=True)


# Reusable instances so routes don't instantiate on every request
register_schema = UserRegisterSchema()
login_schema = UserLoginSchema()
document_upload_schema = DocumentUploadSchema()
analysis_request_schema = AnalysisRequestSchema()
document_response_schema = DocumentResponseSchema()
analysis_response_schema = AnalysisResponseSchema()