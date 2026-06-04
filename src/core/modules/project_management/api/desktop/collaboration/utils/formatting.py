"""Display formatting helpers and label builders for collaboration data."""

from __future__ import annotations

from datetime import datetime

from src.core.platform.documents import DocumentStorageKind


def format_enum_label(value: str) -> str:
    return str(value or "").replace("_", " ").title()


def format_datetime(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M")


def format_document_option_label(document) -> str:
    document_code = str(getattr(document, "document_code", "") or "").strip()
    title = str(getattr(document, "title", "") or "").strip()
    if document_code and title:
        return f"{document_code} - {title}"
    return title or document_code or str(getattr(document, "id", "") or "").strip()


def format_linked_document_label(document) -> str:
    title = (
        str(getattr(document, "file_name", "") or "").strip()
        or str(getattr(document, "title", "") or "").strip()
        or str(getattr(document, "storage_uri", "") or "").strip()
        or str(getattr(document, "document_code", "") or "").strip()
    )
    document_type = (
        str(getattr(getattr(document, "document_type", None), "value", "") or "")
        .replace("_", " ")
        .title()
        or "Document"
    )
    storage_kind = _STORAGE_KIND_LABELS.get(
        getattr(document, "storage_kind", None),
        "Document",
    )
    return f"{title} [{document_type} | {storage_kind}]"


_STORAGE_KIND_LABELS = {
    DocumentStorageKind.FILE_PATH: "File",
    DocumentStorageKind.EXTERNAL_URL: "Link",
    DocumentStorageKind.REFERENCE: "Reference",
}


__all__ = [
    "format_datetime",
    "format_document_option_label",
    "format_enum_label",
    "format_linked_document_label",
]
