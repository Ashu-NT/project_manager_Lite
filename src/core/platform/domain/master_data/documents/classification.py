"""Document confidentiality classification.

`Document.confidentiality_level` stores the classification's value. Stored values that
predate this vocabulary (free text) are read as CONFIDENTIAL so they fail closed: a
document never becomes more visible because its label is unrecognised.
"""

from __future__ import annotations

from enum import StrEnum

from src.core.platform.common.exceptions import ValidationError


class DocumentClassification(StrEnum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


DEFAULT_DOCUMENT_CLASSIFICATION = DocumentClassification.INTERNAL


def parse_document_classification(value: object) -> DocumentClassification:
    """Strict parse for writes: empty means the default; unknown labels are rejected."""
    normalized = str(value or "").strip().upper()
    if not normalized:
        return DEFAULT_DOCUMENT_CLASSIFICATION
    try:
        return DocumentClassification(normalized)
    except ValueError as exc:
        allowed = ", ".join(item.value for item in DocumentClassification)
        raise ValidationError(
            f"Document confidentiality must be one of: {allowed}.",
            code="DOCUMENT_CONFIDENTIALITY_INVALID",
        ) from exc


def stored_document_classification(value: object) -> DocumentClassification:
    """Lenient read of a stored label: empty is the default, unknown fails closed."""
    normalized = str(value or "").strip().upper()
    if not normalized:
        return DEFAULT_DOCUMENT_CLASSIFICATION
    try:
        return DocumentClassification(normalized)
    except ValueError:
        return DocumentClassification.CONFIDENTIAL


__all__ = [
    "DEFAULT_DOCUMENT_CLASSIFICATION",
    "DocumentClassification",
    "parse_document_classification",
    "stored_document_classification",
]
