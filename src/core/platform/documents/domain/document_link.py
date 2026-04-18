from __future__ import annotations

from dataclasses import dataclass

from src.core.platform.common.ids import generate_id


@dataclass
class DocumentLink:
    id: str
    organization_id: str
    document_id: str
    module_code: str
    entity_type: str
    entity_id: str
    link_role: str = ""

    @staticmethod
    def create(
        *,
        organization_id: str,
        document_id: str,
        module_code: str,
        entity_type: str,
        entity_id: str,
        link_role: str = "",
    ) -> "DocumentLink":
        return DocumentLink(
            id=generate_id(),
            organization_id=organization_id,
            document_id=document_id,
            module_code=module_code,
            entity_type=entity_type,
            entity_id=entity_id,
            link_role=link_role,
        )


__all__ = ["DocumentLink"]
