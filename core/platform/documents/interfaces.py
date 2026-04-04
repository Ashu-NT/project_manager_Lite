from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from core.platform.documents.domain import Document, DocumentLink, DocumentStructure


class DocumentStructureRepository(ABC):
    @abstractmethod
    def add(self, structure: DocumentStructure) -> None: ...
    @abstractmethod
    def update(self, structure: DocumentStructure) -> None: ...
    @abstractmethod
    def get(self, structure_id: str) -> Optional[DocumentStructure]: ...
    @abstractmethod
    def get_by_code(self, organization_id: str, structure_code: str) -> Optional[DocumentStructure]: ...
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
    def get(self, document_id: str) -> Optional[Document]: ...
    @abstractmethod
    def get_by_code(self, organization_id: str, document_code: str) -> Optional[Document]: ...
    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
    ) -> list[Document]: ...


class DocumentLinkRepository(ABC):
    @abstractmethod
    def add(self, link: DocumentLink) -> None: ...
    @abstractmethod
    def get(self, link_id: str) -> Optional[DocumentLink]: ...
    @abstractmethod
    def list_for_document(self, document_id: str) -> list[DocumentLink]: ...
    @abstractmethod
    def list_for_entity(self, organization_id: str, module_code: str, entity_type: str, entity_id: str) -> list[DocumentLink]: ...
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
    ) -> Optional[DocumentLink]: ...
    @abstractmethod
    def delete(self, link_id: str) -> None: ...


__all__ = ["DocumentLinkRepository", "DocumentRepository", "DocumentStructureRepository"]
