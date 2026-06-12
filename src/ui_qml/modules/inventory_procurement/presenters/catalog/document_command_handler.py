from __future__ import annotations


def link_document(desktop_api, item_id: str, document_id: str) -> None:
    normalized_item_id = (item_id or "").strip()
    normalized_document_id = (document_id or "").strip()
    if not normalized_item_id:
        raise ValueError("Select an item before linking a document.")
    if not normalized_document_id:
        raise ValueError("Choose a document before saving.")
    desktop_api.link_document(normalized_item_id, document_id=normalized_document_id)


def unlink_document(desktop_api, item_id: str, document_id: str) -> None:
    normalized_item_id = (item_id or "").strip()
    normalized_document_id = (document_id or "").strip()
    if not normalized_item_id:
        raise ValueError("Select an item before unlinking a document.")
    if not normalized_document_id:
        raise ValueError("Choose a linked document before removing it.")
    desktop_api.unlink_document(normalized_item_id, document_id=normalized_document_id)
