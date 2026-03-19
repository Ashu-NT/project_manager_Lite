from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.platform.documents.domain import (
        Document,
        DocumentClassification,
        DocumentLink,
        DocumentStorageKind,
    )
    from core.platform.documents.service import DocumentService

__all__ = [
    "Document",
    "DocumentClassification",
    "DocumentLink",
    "DocumentService",
    "DocumentStorageKind",
]


def __getattr__(name: str):
    if name == "Document":
        from core.platform.documents.domain import Document

        return Document
    if name == "DocumentClassification":
        from core.platform.documents.domain import DocumentClassification

        return DocumentClassification
    if name == "DocumentLink":
        from core.platform.documents.domain import DocumentLink

        return DocumentLink
    if name == "DocumentStorageKind":
        from core.platform.documents.domain import DocumentStorageKind

        return DocumentStorageKind
    if name == "DocumentService":
        from core.platform.documents.service import DocumentService

        return DocumentService
    raise AttributeError(name)
