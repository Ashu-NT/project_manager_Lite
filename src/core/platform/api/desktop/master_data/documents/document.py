from __future__ import annotations

from src.core.platform.api.desktop.master_data.documents.models.document import (
    DocumentDto,
    DocumentLinkDto,
    DocumentPageDto,
    DocumentRollupSummaryDto,
    DocumentStructureDto,
)
from src.core.platform.api.desktop.master_data.org.models.organization import (
    OrganizationDto,
)
from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.platform.api.desktop.support._support import (
    execute_desktop_operation,
    serialize_organization,
)
from src.core.platform.application.master_data.documents import (
    DocumentCommandHandler,
    DocumentQueryHandler,
    DocumentStructureCommandHandler,
)
from src.core.platform.contract.use_cases.master_data.documents.commands import (
    DocumentCreateCommand,
    DocumentLinkCreateCommand,
    DocumentStructureCreateCommand,
    DocumentStructureUpdateCommand,
    DocumentUpdateCommand,
)
from src.core.platform.domain.master_data.documents import (
    Document,
    DocumentLink,
    DocumentStructure,
)


class PlatformDocumentDesktopApi:
    """Desktop-facing adapter for platform document administration flows."""

    def __init__(
        self,
        *,
        document_commands: DocumentCommandHandler,
        document_structure_commands: DocumentStructureCommandHandler,
        document_query: DocumentQueryHandler,
    ) -> None:
        self._document_commands = document_commands
        self._document_structure_commands = document_structure_commands
        self._document_query = document_query

    def get_context(self) -> DesktopApiResult[OrganizationDto]:
        return execute_desktop_operation(
            lambda: serialize_organization(self._document_query.get_context_organization())
        )

    def list_documents(
        self,
        *,
        active_only: bool | None = None,
    ) -> DesktopApiResult[tuple[DocumentDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                self._serialize_document(document)
                for document in self._document_query.list_documents(active_only=active_only)
            )
        )

    def list_documents_page_for_organization(
        self,
        organization_id: str,
        *,
        page: int = 1,
        page_size: int = 25,
        search: str = "",
        active_only: bool | None = None,
    ) -> DesktopApiResult[DocumentPageDto]:
        return execute_desktop_operation(
            lambda: self._serialize_document_page(
                self._document_query.list_documents_page_for_organization(
                    organization_id,
                    page=page,
                    page_size=page_size,
                    search=search,
                    active_only=active_only,
                )
            )
        )

    def get_document(self, document_id: str) -> DesktopApiResult[DocumentDto]:
        return execute_desktop_operation(
            lambda: self._serialize_document(self._document_query.get_document(document_id))
        )

    def list_documents_page_for_entity(
        self,
        *,
        module_code: str,
        entity_type: str,
        entity_id: str,
        page: int = 1,
        page_size: int = 25,
        search: str = "",
        active_only: bool | None = None,
        document_type: str | None = None,
    ) -> DesktopApiResult[DocumentPageDto]:
        return execute_desktop_operation(
            lambda: self._serialize_entity_document_page(
                self._document_query.list_documents_page_for_entity(
                    module_code=module_code,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    page=page,
                    page_size=page_size,
                    search=search,
                    active_only=active_only,
                    document_type=document_type,
                )
            )
        )

    def get_document_rollup_summary(self) -> DesktopApiResult[DocumentRollupSummaryDto]:
        return execute_desktop_operation(
            lambda: self._serialize_rollup_summary(
                self._document_query.get_document_rollup_summary()
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
                for structure in self._document_query.list_document_structures(
                    active_only=active_only,
                    object_scope=object_scope,
                )
            )
        )

    def create_document(self, command: DocumentCreateCommand) -> DesktopApiResult[DocumentDto]:
        return execute_desktop_operation(
            lambda: self._serialize_document(
                self._document_commands.create_document(command)
            )
        )

    def update_document(self, command: DocumentUpdateCommand) -> DesktopApiResult[DocumentDto]:
        return execute_desktop_operation(
            lambda: self._serialize_document(
                self._document_commands.update_document(command)
            )
        )

    def create_document_structure(
        self,
        command: DocumentStructureCreateCommand,
    ) -> DesktopApiResult[DocumentStructureDto]:
        return execute_desktop_operation(
            lambda: self._serialize_document_structure(
                self._document_structure_commands.create_document_structure(command)
            )
        )

    def update_document_structure(
        self,
        command: DocumentStructureUpdateCommand,
    ) -> DesktopApiResult[DocumentStructureDto]:
        return execute_desktop_operation(
            lambda: self._serialize_document_structure(
                self._document_structure_commands.update_document_structure(command)
            )
        )

    def list_links(self, document_id: str) -> DesktopApiResult[tuple[DocumentLinkDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                self._serialize_document_link(link)
                for link in self._document_query.list_links(document_id)
            )
        )

    def add_link(self, command: DocumentLinkCreateCommand) -> DesktopApiResult[DocumentLinkDto]:
        return execute_desktop_operation(
            lambda: self._serialize_document_link(
                self._document_commands.add_link(command)
            )
        )

    def remove_link(self, link_id: str) -> DesktopApiResult[None]:
        return execute_desktop_operation(
            lambda: self._document_commands.remove_link(link_id)
        )

    def _serialize_document_page(self, page) -> DocumentPageDto:
        return DocumentPageDto(
            items=tuple(self._serialize_document(document) for document in page.items),
            total=page.total,
            filtered_total=page.filtered_total,
            page=page.page,
            page_size=page.page_size,
        )

    def _serialize_entity_document_page(self, page) -> DocumentPageDto:
        return DocumentPageDto(
            items=tuple(
                self._serialize_document(row.document, link_id=row.link.id) for row in page.items
            ),
            total=page.total,
            filtered_total=page.filtered_total,
            page=page.page,
            page_size=page.page_size,
        )

    @staticmethod
    def _serialize_rollup_summary(summary) -> DocumentRollupSummaryDto:
        return DocumentRollupSummaryDto(total=summary.total, current=summary.current)

    @staticmethod
    def _serialize_document(document: Document, *, link_id: str = "") -> DocumentDto:
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
            link_id=link_id,
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
