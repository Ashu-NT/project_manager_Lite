"""SQL form of `DocumentVisibility`, so pages and totals never include hidden documents."""

from __future__ import annotations

from sqlalchemy import ColumnElement, and_, case, exists, false, func, or_, select

from src.core.platform.contract.port.master_data.documents.document_access_policy import (
    DocumentVisibility,
)
from src.core.platform.domain.master_data.documents.classification import (
    DEFAULT_DOCUMENT_CLASSIFICATION,
    DocumentClassification,
)
from src.core.platform.infrastructure.persistence.orm.master_data.documents.documents import (
    DocumentLinkORM,
    DocumentORM,
)

_KNOWN = tuple(item.value for item in DocumentClassification)


def effective_classification() -> ColumnElement[str]:
    """Mirrors `stored_document_classification`: empty is the default, unknown fails closed."""
    level = func.upper(func.trim(func.coalesce(DocumentORM.confidentiality_level, "")))
    return case(
        (level == "", DEFAULT_DOCUMENT_CLASSIFICATION.value),
        (level.in_(_KNOWN), level),
        else_=DocumentClassification.CONFIDENTIAL.value,
    )


def document_visibility_condition(visibility: DocumentVisibility) -> ColumnElement[bool]:
    classification = effective_classification()
    clauses: list[ColumnElement[bool]] = []
    visible = sorted(item.value for item in visibility.classifications)
    if visible:
        clauses.append(classification.in_(visible))
    for grant in visibility.restricted_grants:
        link_match = [
            DocumentLinkORM.document_id == DocumentORM.id,
            DocumentLinkORM.entity_type == grant.entity_type,
        ]
        if grant.entity_ids is not None:
            if not grant.entity_ids:
                continue
            link_match.append(DocumentLinkORM.entity_id.in_(sorted(grant.entity_ids)))
        clauses.append(
            and_(
                classification == DocumentClassification.RESTRICTED.value,
                exists(select(DocumentLinkORM.id).where(*link_match)),
            )
        )
    return or_(*clauses) if clauses else false()


__all__ = ["document_visibility_condition", "effective_classification"]
