from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentLinkCreateCommand:
    document_id: str
    module_code: str
    entity_type: str
    entity_id: str
    link_role: str = ""
