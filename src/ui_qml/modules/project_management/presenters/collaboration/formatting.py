from __future__ import annotations

from datetime import UTC, datetime


def iso_datetime(value: datetime | None) -> str:
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


def format_timestamp(value: datetime | None) -> str:
    if value is None:
        return "Timestamp unavailable"
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).strftime("%Y-%m-%d %H:%M")


def mentions_label(mentions) -> str:
    return (
        ", ".join(f"@{str(value).strip()}" for value in mentions if str(value).strip())
        or "No direct mentions"
    )


def body_preview(item) -> str:
    return "This comment was deleted." if item.is_deleted else item.body_preview


def format_document_option_label(document) -> str:
    code = str(document.document_code or "").strip()
    title = str(document.title or "").strip()
    return f"{code} - {title}" if code and title else title or code or document.id


def format_linked_document_label(document) -> str:
    from src.core.platform.domain.master_data.documents import DocumentStorageKind

    title = (
        (document.file_name or "").strip()
        or (document.title or "").strip()
        or str(getattr(document, "storage_uri", "") or "").strip()
        or (document.document_code or "").strip()
    )
    document_type = (
        str(document.document_type.value or "").replace("_", " ").title() or "Document"
    )
    storage = {
        DocumentStorageKind.FILE_PATH: "File",
        DocumentStorageKind.EXTERNAL_URL: "Link",
        DocumentStorageKind.REFERENCE: "Reference",
    }.get(document.storage_kind, "Document")
    return f"{title} [{document_type} | {storage}]"
