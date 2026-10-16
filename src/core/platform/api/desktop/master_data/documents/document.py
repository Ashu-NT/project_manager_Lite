from __future__ import annotations

from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.platform.api.desktop.support._support import (
    execute_desktop_operation,
)
from src.core.platform.application.master_data.documents import (
    DocumentCommandHandler,
    DocumentQueryHandler,
    DocumentStructureCommandHandler,
)
from src.core.platform.application.master_data.documents.dto.commands.documents import (
    DocumentCreateCommand,
    DocumentUpdateCommand,
)
from src.core.platform.application.master_data.documents.dto.commands.links import (
    DocumentLinkCreateCommand,
)
from src.core.platform.application.master_data.documents.dto.commands.structures import (
    DocumentStructureCreateCommand,
    DocumentStructureUpdateCommand,
)
from src.core.platform.application.master_data.documents.dto.responses.document import (
    DocumentDto,
    DocumentLinkDto,
    DocumentPageDto,
    DocumentStructureDto,
)
from src.core.platform.application.master_data.org.dto.responses.organization import (
    OrganizationDto,
)
from src.core.platform.contract.read.overview.platform_overview_rollup_reader import (
    DocumentRollupSummary,
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
            lambda: self._document_query.get_context_organization()
        )

    def list_documents(
        self,
        *,
        active_only: bool | None = None,
    ) -> DesktopApiResult[tuple[DocumentDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                document
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
            lambda: self._document_query.list_documents_page_for_organization(
                    organization_id,
                    page=page,
                    page_size=page_size,
                    search=search,
                    active_only=active_only,
                )
        )

    def get_document(self, document_id: str) -> DesktopApiResult[DocumentDto]:
        return execute_desktop_operation(
            lambda: self._document_query.get_document(document_id)
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
            lambda: self._document_query.list_documents_page_for_entity(
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

    def get_document_rollup_summary(self) -> DesktopApiResult[DocumentRollupSummary]:
        return execute_desktop_operation(
            lambda: self._document_query.get_document_rollup_summary()
        )

    def list_document_structures(
        self,
        *,
        active_only: bool | None = None,
        object_scope: str | None = None,
    ) -> DesktopApiResult[tuple[DocumentStructureDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                structure
                for structure in self._document_query.list_document_structures(
                    active_only=active_only,
                    object_scope=object_scope,
                )
            )
        )

    def create_document(self, command: DocumentCreateCommand) -> DesktopApiResult[DocumentDto]:
        return execute_desktop_operation(
            lambda: self._document_commands.create_document(command)
        )

    def update_document(self, command: DocumentUpdateCommand) -> DesktopApiResult[DocumentDto]:
        return execute_desktop_operation(
            lambda: self._document_commands.update_document(command)
        )

    def create_document_structure(
        self,
        command: DocumentStructureCreateCommand,
    ) -> DesktopApiResult[DocumentStructureDto]:
        return execute_desktop_operation(
            lambda: self._document_structure_commands.create_document_structure(command)
        )

    def update_document_structure(
        self,
        command: DocumentStructureUpdateCommand,
    ) -> DesktopApiResult[DocumentStructureDto]:
        return execute_desktop_operation(
            lambda: self._document_structure_commands.update_document_structure(command)
        )

    def list_links(self, document_id: str) -> DesktopApiResult[tuple[DocumentLinkDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                link
                for link in self._document_query.list_links(document_id)
            )
        )

    def add_link(self, command: DocumentLinkCreateCommand) -> DesktopApiResult[DocumentLinkDto]:
        return execute_desktop_operation(
            lambda: self._document_commands.add_link(command)
        )

    def remove_link(self, link_id: str) -> DesktopApiResult[None]:
        return execute_desktop_operation(
            lambda: self._document_commands.remove_link(link_id)
        )








__all__ = ["PlatformDocumentDesktopApi"]
