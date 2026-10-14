"""Document visibility contract.

Documents never decide visibility from a broad setting. A `DocumentAccessPolicy` resolves,
for the current principal, a `DocumentVisibility`: which classifications are always
visible, plus which entity-linked RESTRICTED documents are visible. Modules that own an
entity type (for example a future HR module for employee contracts) contribute a
`RestrictedDocumentRule`; Documents itself has no knowledge of those modules.

Visibility is expressed as data, not as a per-document callback, so readers and
repositories can enforce it inside SQL (filters, totals and pagination never reveal
hidden documents).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.core.platform.domain.master_data.documents.classification import (
    DocumentClassification,
    stored_document_classification,
)
from src.core.platform.domain.security.auth.session import UserSessionPrincipal


@dataclass(frozen=True)
class RestrictedDocumentGrant:
    """RESTRICTED documents linked to `entity_type` that the viewer may see.

    `entity_ids=None` grants every entity of that type (e.g. an HR officer for all
    employees); otherwise only documents linked to one of the listed entity ids.
    """

    entity_type: str
    entity_ids: frozenset[str] | None


@dataclass(frozen=True)
class DocumentVisibility:
    classifications: frozenset[DocumentClassification]
    restricted_grants: tuple[RestrictedDocumentGrant, ...] = ()

    def allows(
        self,
        confidentiality_level: object,
        links: tuple[tuple[str, str], ...] = (),
    ) -> bool:
        classification = stored_document_classification(confidentiality_level)
        if classification in self.classifications:
            return True
        if classification is not DocumentClassification.RESTRICTED:
            return False
        for entity_type, entity_id in links:
            for grant in self.restricted_grants:
                if grant.entity_type == entity_type and (
                    grant.entity_ids is None or entity_id in grant.entity_ids
                ):
                    return True
        return False


class RestrictedDocumentRule(Protocol):
    """Contributed by the module that owns `entity_type`."""

    @property
    def entity_type(self) -> str: ...

    def grant_for(self, principal: UserSessionPrincipal) -> RestrictedDocumentGrant | None: ...


class DocumentAccessPolicy(Protocol):
    def visibility(self) -> DocumentVisibility: ...

    def register_rule(self, rule: RestrictedDocumentRule) -> None: ...


__all__ = [
    "DocumentAccessPolicy",
    "DocumentVisibility",
    "RestrictedDocumentGrant",
    "RestrictedDocumentRule",
]
