from __future__ import annotations

from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.domain.master_data.documents import Document, DocumentStructure
from src.core.platform.domain.master_data.documents.support import normalize_optional_text
from src.core.platform.domain.master_data.org import Organization


def active_organization(service) -> Organization:
    if service._tenant_context_service is None:
        raise BusinessRuleError(
            "Active organization context is required.",
            code="TENANT_CONTEXT_REQUIRED",
        )
    organization = service._tenant_context_service.get_active_organization()
    if organization is None:
        raise BusinessRuleError(
            "Active organization context is required.",
            code="TENANT_CONTEXT_REQUIRED",
        )
    return organization


def resolve_structure_for_context(
    structure_id: str | None,
    *,
    organization: Organization,
    structure_repo,
) -> DocumentStructure | None:
    normalized_id = normalize_optional_text(structure_id)
    if not normalized_id:
        return None
    structure = structure_repo.get(normalized_id)
    if structure is None or structure.organization_id != organization.id:
        raise NotFoundError(
            "Document structure not found in the active organization.",
            code="DOCUMENT_STRUCTURE_NOT_FOUND",
        )
    return structure


def require_document_in_context(
    document_id: str,
    *,
    organization: Organization,
    document_repo,
) -> Document:
    document = document_repo.get(document_id)
    if document is None or document.organization_id != organization.id:
        raise NotFoundError("Document not found in the active organization.", code="DOCUMENT_NOT_FOUND")
    return document


__all__ = [
    "active_organization",
    "require_document_in_context",
    "resolve_structure_for_context",
]
