from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.platform.domain.master_data.documents import (
    Document,
    DocumentLink,
    DocumentStructure,
)


class DocumentStructureRepository(ABC):
    @abstractmethod
    def add(self, structure: DocumentStructure) -> None: ...

    @abstractmethod
    def update(self, structure: DocumentStructure) -> None: ...

    @abstractmethod
    def get(self, structure_id: str) -> DocumentStructure | None: ...

    @abstractmethod
    def get_by_code(self, organization_id: str, structure_code: str) -> DocumentStructure | None: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
        object_scope: str | None = None,
    ) -> list[DocumentStructure]: ...


class DocumentRepository(ABC):
    @abstractmethod
    def add(self, document: Document) -> None: ...

    @abstractmethod
    def update(self, document: Document) -> None: ...

    @abstractmethod
    def get(self, document_id: str) -> Document | None: ...

    @abstractmethod
    def get_by_code(self, organization_id: str, document_code: str) -> Document | None: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
    ) -> list[Document]: ...

    @abstractmethod
    def list_page_for_organization_in_tenant(
        self,
        organization_id: str,
        tenant_id: str,
        *,
        page: int,
        page_size: int,
        search: str | None = None,
        active_only: bool | None = None,
    ) -> tuple[list[Document], int, int]:
        """Tenant-scoped only -- NOT filtered to the ambient active
        organization. For an admin viewing ANY organization's documents
        (e.g. Organization Detail's Documents tab) regardless of which
        organization is currently active in the caller's session. Returns
        (page_items, total_count, filtered_total_count)."""
        ...


class DocumentLinkRepository(ABC):
    @abstractmethod
    def add(self, link: DocumentLink) -> None: ...

    @abstractmethod
    def get(self, link_id: str) -> DocumentLink | None: ...

    @abstractmethod
    def list_for_document(self, document_id: str) -> list[DocumentLink]: ...

    @abstractmethod
    def list_for_entity(
        self,
        organization_id: str,
        module_code: str,
        entity_type: str,
        entity_id: str,
    ) -> list[DocumentLink]: ...

    @abstractmethod
    def list_for_module(
        self,
        organization_id: str,
        module_code: str,
        *,
        entity_type: str | None = None,
    ) -> list[DocumentLink]: ...

    @abstractmethod
    def find_existing(
        self,
        *,
        document_id: str,
        module_code: str,
        entity_type: str,
        entity_id: str,
        link_role: str,
    ) -> DocumentLink | None: ...

    @abstractmethod
    def delete(self, link_id: str) -> None: ...


__all__ = [
    "DocumentLinkRepository",
    "DocumentRepository",
    "DocumentStructureRepository",
]
