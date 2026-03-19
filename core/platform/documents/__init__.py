from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.platform.documents.domain import (
        Document,
        DocumentClassification,
        DocumentLink,
        DocumentStorageKind,
        DocumentType,
    )
    from core.platform.documents.integration_service import DocumentIntegrationService
    from core.platform.documents.service import DocumentService

__all__ = [
    "Document",
    "DocumentClassification",
    "DocumentIntegrationService",
    "DocumentLink",
    "DocumentService",
    "DocumentStorageKind",
    "DocumentType",
]


def __getattr__(name: str):
    if name == "Document":
        from core.platform.documents.domain import Document

        return Document
    if name == "DocumentClassification":
        from core.platform.documents.domain import DocumentClassification

        return DocumentClassification
    if name == "DocumentIntegrationService":
        from core.platform.documents.integration_service import DocumentIntegrationService

        return DocumentIntegrationService
    if name == "DocumentLink":
        from core.platform.documents.domain import DocumentLink

        return DocumentLink
    if name == "DocumentStorageKind":
        from core.platform.documents.domain import DocumentStorageKind

        return DocumentStorageKind
    if name == "DocumentService":
        from core.platform.documents.service import DocumentService

        return DocumentService
    if name == "DocumentType":
        from core.platform.documents.domain import DocumentType

        return DocumentType
    raise AttributeError(name)
