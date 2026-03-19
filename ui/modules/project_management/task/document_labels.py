from __future__ import annotations

from core.platform.documents import Document, DocumentStorageKind


_STORAGE_KIND_LABELS = {
    DocumentStorageKind.FILE_PATH: "File",
    DocumentStorageKind.EXTERNAL_URL: "Link",
    DocumentStorageKind.REFERENCE: "Reference",
}


def format_linked_document_label(document: Document) -> str:
    title = (document.file_name or document.title or document.storage_uri or document.document_code).strip()
    document_type = document.document_type.value.replace("_", " ").title()
    storage_kind = _STORAGE_KIND_LABELS.get(document.storage_kind, "Document")
    return f"{title} [{document_type} | {storage_kind}]"


__all__ = ["format_linked_document_label"]
