"""Permission-based document visibility for the current session."""

from __future__ import annotations

from src.core.platform.application.security.authorization import (
    get_authorization_engine,
)
from src.core.platform.contract.port.master_data.documents.document_access_policy import (
    DocumentVisibility,
    RestrictedDocumentGrant,
    RestrictedDocumentRule,
)
from src.core.platform.contract.repositories.master_data.documents.contracts import (
    DocumentLinkRepository,
)
from src.core.platform.domain.master_data.documents import Document
from src.core.platform.domain.master_data.documents.classification import (
    DocumentClassification,
)
from src.core.platform.domain.security.auth.session import UserSessionContext

DOCUMENT_READ_PERMISSION = "document.read"
DOCUMENT_MANAGE_PERMISSION = "document.manage"
DOCUMENT_STRUCTURE_MANAGE_PERMISSION = "document.structure.manage"
DOCUMENT_CONFIDENTIAL_READ_PERMISSION = "document.confidential.read"


class PermissionDocumentAccessPolicy:
    """PUBLIC/INTERNAL need `document.read`; CONFIDENTIAL additionally needs
    `document.confidential.read`; RESTRICTED is never granted by role, only by a
    rule registered by the module that owns the linked entity."""

    def __init__(self, *, user_session: UserSessionContext | None) -> None:
        self._user_session = user_session
        self._rules: dict[str, RestrictedDocumentRule] = {}

    def register_rule(self, rule: RestrictedDocumentRule) -> None:
        if rule.entity_type in self._rules:
            raise ValueError(f"A restricted-document rule for {rule.entity_type!r} is already registered.")
        self._rules[rule.entity_type] = rule

    def visibility(self) -> DocumentVisibility:
        principal = self._user_session.principal if self._user_session is not None else None
        if principal is None:
            return DocumentVisibility(classifications=frozenset())
        engine = get_authorization_engine()
        classifications: set[DocumentClassification] = set()
        if engine.has_permission(self._user_session, DOCUMENT_READ_PERMISSION):
            classifications |= {DocumentClassification.PUBLIC, DocumentClassification.INTERNAL}
            if engine.has_permission(self._user_session, DOCUMENT_CONFIDENTIAL_READ_PERMISSION):
                classifications.add(DocumentClassification.CONFIDENTIAL)
        grants: list[RestrictedDocumentGrant] = []
        for rule in self._rules.values():
            grant = rule.grant_for(principal)
            if grant is not None and grant.entity_type == rule.entity_type:
                grants.append(grant)
        return DocumentVisibility(classifications=frozenset(classifications), restricted_grants=tuple(grants))


def attachment_visibility(visibility: DocumentVisibility) -> DocumentVisibility:
    """Entity-attachment reads are authorized by the owning module's permission, which
    stands in for `document.read` on PUBLIC/INTERNAL documents only. CONFIDENTIAL still
    needs `document.confidential.read`; RESTRICTED still needs a module rule."""
    return DocumentVisibility(
        classifications=visibility.classifications
        | {DocumentClassification.PUBLIC, DocumentClassification.INTERNAL},
        restricted_grants=visibility.restricted_grants,
    )


def is_document_visible(
    document: Document,
    visibility: DocumentVisibility,
    link_repo: DocumentLinkRepository,
) -> bool:
    if visibility.allows(document.confidentiality_level):
        return True
    if not visibility.restricted_grants:
        return False
    links = tuple((link.entity_type, link.entity_id) for link in link_repo.list_for_document(document.id))
    return visibility.allows(document.confidentiality_level, links)


__all__ = [
    "DOCUMENT_CONFIDENTIAL_READ_PERMISSION",
    "DOCUMENT_MANAGE_PERMISSION",
    "DOCUMENT_READ_PERMISSION",
    "DOCUMENT_STRUCTURE_MANAGE_PERMISSION",
    "PermissionDocumentAccessPolicy",
    "attachment_visibility",
    "is_document_visible",
]
