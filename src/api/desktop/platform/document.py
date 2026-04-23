from __future__ import annotations

from src.api.desktop.platform._support import execute_desktop_operation, serialize_organization
from src.api.desktop.platform.models import (
    DesktopApiResult,
    DocumentCreateCommand,
    DocumentDto,
    DocumentLinkCreateCommand,
    DocumentLinkDto,
    DocumentStructureCreateCommand,
    DocumentStructureDto,
    DocumentStructureUpdateCommand,
    DocumentUpdateCommand,
    OrganizationDto,
)
from src.core.platform.documents import DocumentService
from src.core.platform.documents.domain import Document, DocumentLink, DocumentStructure


class PlatformDocumentDesktopApi:
    """Desktop-facing adapter for platform document administration flows."""

    def __init__(self, *, document_service: DocumentService) -> None:
        self._document_service = document_service

    def get_context(self) -> DesktopApiResult[OrganizationDto]:
        return execute_desktop_operation(
            lambda: serialize_organization(self._document_service.get_context_organization())
        )

    def list_documents(
        self,
        *,
        active_only: bool | None = None,
    ) -> DesktopApiResult[tuple[DocumentDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                self._serialize_document(document)
                for document in self._document_service.list_documents(active_only=active_only)
            )
        )

    def list_document_structures(
        self,
        *,
        active_only: bool | None = None,
        object_scope: str | None = None,
    ) -> DesktopApiResult[tuple[DocumentStructureDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                self._serialize_document_structure(structure)
                for structure in self._document_service.list_document_structures(
                    active_only=active_only,
                    object_scope=object_scope,
                )
            )
        )

    def create_document(self, command: DocumentCreateCommand) -> DesktopApiResult[DocumentDto]:
        return execute_desktop_operation(
            lambda: self._serialize_document(
                self._document_service.create_document(
                    document_code=command.document_code,
                    title=command.title,
                    document_type=command.document_type,
                    document_structure_id=command.document_structure_id,
                    storage_kind=command.storage_kind,
                    storage_uri=command.storage_uri,
                    file_name=command.file_name,
                    mime_type=command.mime_type,
                    source_system=command.source_system,
                    uploaded_at=command.uploaded_at,
                    uploaded_by_user_id=command.uploaded_by_user_id,
                    effective_date=command.effective_date,
                    review_date=command.review_date,
                    confidentiality_level=command.confidentiality_level,
                    business_version_label=command.business_version_label,
                    is_current=command.is_current,
                    notes=command.notes,
                    is_active=command.is_active,
                )
            )
        )

    def update_document(self, command: DocumentUpdateCommand) -> DesktopApiResult[DocumentDto]:
        return execute_desktop_operation(
            lambda: self._serialize_document(
                self._document_service.update_document(
                    command.document_id,
                    document_code=command.document_code,
                    title=command.title,
                    document_type=command.document_type,
                    document_structure_id=command.document_structure_id,
                    storage_kind=command.storage_kind,
                    storage_uri=command.storage_uri,
                    file_name=command.file_name,
                    mime_type=command.mime_type,
                    source_system=command.source_system,
                    uploaded_at=command.uploaded_at,
                    uploaded_by_user_id=command.uploaded_by_user_id,
                    effective_date=command.effective_date,
                    review_date=command.review_date,
                    confidentiality_level=command.confidentiality_level,
                    business_version_label=command.business_version_label,
                    is_current=command.is_current,
                    notes=command.notes,
                    is_active=command.is_active,
                    expected_version=command.expected_version,
                )
            )
        )

    def create_document_structure(
        self,
        command: DocumentStructureCreateCommand,
    ) -> DesktopApiResult[DocumentStructureDto]:
        return execute_desktop_operation(
            lambda: self._serialize_document_structure(
                self._document_service.create_document_structure(
                    structure_code=command.structure_code,
                    name=command.name,
                    description=command.description,
                    parent_structure_id=command.parent_structure_id,
                    object_scope=command.object_scope,
                    default_document_type=command.default_document_type,
                    sort_order=command.sort_order,
                    is_active=command.is_active,
                    notes=command.notes,
                )
            )
        )

    def update_document_structure(
        self,
        command: DocumentStructureUpdateCommand,
    ) -> DesktopApiResult[DocumentStructureDto]:
        return execute_desktop_operation(
            lambda: self._serialize_document_structure(
                self._document_service.update_document_structure(
                    command.structure_id,
                    structure_code=command.structure_code,
                    name=command.name,
                    description=command.description,
                    parent_structure_id=command.parent_structure_id,
                    object_scope=command.object_scope,
                    default_document_type=command.default_document_type,
                    sort_order=command.sort_order,
                    is_active=command.is_active,
                    notes=command.notes,
                    expected_version=command.expected_version,
                )
            )
        )

    def list_links(self, document_id: str) -> DesktopApiResult[tuple[DocumentLinkDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                self._serialize_document_link(link)
                for link in self._document_service.list_links(document_id)
            )
        )

    def add_link(self, command: DocumentLinkCreateCommand) -> DesktopApiResult[DocumentLinkDto]:
        return execute_desktop_operation(
            lambda: self._serialize_document_link(
                self._document_service.add_link(
                    document_id=command.document_id,
                    module_code=command.module_code,
                    entity_type=command.entity_type,
                    entity_id=command.entity_id,
                    link_role=command.link_role,
                )
            )
        )

    def remove_link(self, link_id: str) -> DesktopApiResult[None]:
        return execute_desktop_operation(
            lambda: self._document_service.remove_link(link_id)
        )

    @staticmethod
    def _serialize_document(document: Document) -> DocumentDto:
        return DocumentDto(
            id=document.id,
            organization_id=document.organization_id,
            document_code=document.document_code,
            title=document.title,
            document_type=document.document_type,
            document_structure_id=document.document_structure_id,
            storage_kind=document.storage_kind,
            storage_uri=document.storage_uri,
            file_name=document.file_name,
            mime_type=document.mime_type,
            source_system=document.source_system,
            uploaded_at=document.uploaded_at,
            uploaded_by_user_id=document.uploaded_by_user_id,
            effective_date=document.effective_date,
            review_date=document.review_date,
            confidentiality_level=document.confidentiality_level,
            business_version_label=document.business_version_label,
            is_current=document.is_current,
            notes=document.notes,
            is_active=document.is_active,
            version=document.version,
        )

    @staticmethod
    def _serialize_document_structure(structure: DocumentStructure) -> DocumentStructureDto:
        return DocumentStructureDto(
            id=structure.id,
            organization_id=structure.organization_id,
            structure_code=structure.structure_code,
            name=structure.name,
            description=structure.description,
            parent_structure_id=structure.parent_structure_id,
            object_scope=structure.object_scope,
            default_document_type=structure.default_document_type,
            sort_order=structure.sort_order,
            is_active=structure.is_active,
            notes=structure.notes,
            version=structure.version,
        )

    @staticmethod
    def _serialize_document_link(link: DocumentLink) -> DocumentLinkDto:
        return DocumentLinkDto(
            id=link.id,
            organization_id=link.organization_id,
            document_id=link.document_id,
            module_code=link.module_code,
            entity_type=link.entity_type,
            entity_id=link.entity_id,
            link_role=link.link_role,
        )


__all__ = ["PlatformDocumentDesktopApi"]
