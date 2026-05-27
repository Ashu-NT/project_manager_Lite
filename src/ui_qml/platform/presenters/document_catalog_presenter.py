from __future__ import annotations

from typing import Any

from src.api.desktop.platform import (
    DocumentCreateCommand,
    DocumentDto,
    DocumentStructureDto,
    DocumentUpdateCommand,
    PlatformDocumentDesktopApi,
)
from src.api.desktop.platform.models import DesktopApiResult
from src.core.platform.documents.domain import DocumentStorageKind, DocumentType
from src.ui_qml.platform.presenters.support import (
    bool_value,
    int_value,
    option_item,
    optional_string_value,
    preview_error_result,
    string_value,
    title_case_code,
)
from src.ui_qml.platform.view_models import (
    PlatformWorkspaceActionItemViewModel,
    PlatformWorkspaceActionListViewModel,
)


class PlatformDocumentCatalogPresenter:
    def __init__(self, *, document_api: PlatformDocumentDesktopApi | None = None) -> None:
        self._document_api = document_api

    def build_catalog(self) -> PlatformWorkspaceActionListViewModel:
        if self._document_api is None:
            return PlatformWorkspaceActionListViewModel(
                title="Documents",
                subtitle="Controlled document records appear here once the platform document API is connected.",
                empty_state="Platform document API is not connected in this QML preview.",
            )

        context_result = self._document_api.get_context()
        documents_result = self._document_api.list_documents(active_only=None)
        structure_lookup = self._structure_lookup()
        if not documents_result.ok or documents_result.data is None:
            message = (
                documents_result.error.message
                if documents_result.error is not None
                else "Unable to load documents."
            )
            return PlatformWorkspaceActionListViewModel(
                title="Documents",
                subtitle=message,
                empty_state=message,
            )

        context_label = (
            context_result.data.display_name
            if context_result.ok and context_result.data is not None
            else "Context unavailable"
        )
        return PlatformWorkspaceActionListViewModel(
            title="Documents",
            subtitle=f"Controlled document metadata and classification for {context_label}.",
            empty_state="No documents are available yet.",
            items=tuple(
                self._serialize_document(row, structure_lookup=structure_lookup)
                for row in documents_result.data
            ),
        )

    def build_type_options(self) -> tuple[dict[str, str], ...]:
        return tuple(
            option_item(
                label=title_case_code(document_type),
                value=document_type.value,
            )
            for document_type in DocumentType
        )

    def build_storage_kind_options(self) -> tuple[dict[str, str], ...]:
        return tuple(
            option_item(
                label=title_case_code(storage_kind),
                value=storage_kind.value,
            )
            for storage_kind in DocumentStorageKind
        )

    def build_structure_options(self) -> tuple[dict[str, str], ...]:
        if self._document_api is None:
            return ()
        result = self._document_api.list_document_structures(active_only=None)
        if not result.ok or result.data is None:
            return ()
        return tuple(self._serialize_structure_option(row) for row in result.data)

    def create_document(self, payload: dict[str, Any]) -> DesktopApiResult[DocumentDto]:
        if self._document_api is None:
            return preview_error_result("Platform document API is not connected in this QML preview.")
        return self._document_api.create_document(
            DocumentCreateCommand(
                document_code=string_value(payload, "documentCode"),
                title=string_value(payload, "title"),
                document_type=string_value(payload, "documentType", default=DocumentType.GENERAL.value),
                document_structure_id=optional_string_value(payload, "documentStructureId"),
                storage_kind=string_value(
                    payload,
                    "storageKind",
                    default=DocumentStorageKind.FILE_PATH.value,
                ),
                storage_uri=string_value(payload, "storageUri"),
                file_name=string_value(payload, "fileName"),
                mime_type=string_value(payload, "mimeType"),
                source_system=string_value(payload, "sourceSystem"),
                confidentiality_level=string_value(payload, "confidentialityLevel"),
                business_version_label=string_value(payload, "businessVersionLabel"),
                is_current=bool_value(payload, "isCurrent", default=True),
                notes=string_value(payload, "notes"),
                is_active=bool_value(payload, "isActive", default=True),
            )
        )

    def update_document(self, payload: dict[str, Any]) -> DesktopApiResult[DocumentDto]:
        if self._document_api is None:
            return preview_error_result("Platform document API is not connected in this QML preview.")
        return self._document_api.update_document(
            DocumentUpdateCommand(
                document_id=string_value(payload, "documentId"),
                document_code=string_value(payload, "documentCode"),
                title=string_value(payload, "title"),
                document_type=string_value(payload, "documentType", default=DocumentType.GENERAL.value),
                document_structure_id=optional_string_value(payload, "documentStructureId"),
                storage_kind=string_value(
                    payload,
                    "storageKind",
                    default=DocumentStorageKind.FILE_PATH.value,
                ),
                storage_uri=string_value(payload, "storageUri"),
                file_name=string_value(payload, "fileName"),
                mime_type=string_value(payload, "mimeType"),
                source_system=string_value(payload, "sourceSystem"),
                confidentiality_level=string_value(payload, "confidentialityLevel"),
                business_version_label=string_value(payload, "businessVersionLabel"),
                is_current=bool_value(payload, "isCurrent", default=True),
                notes=string_value(payload, "notes"),
                is_active=bool_value(payload, "isActive", default=True),
            )
        )

    def toggle_document_active(
        self,
        *,
        document_id: str,
        is_active: bool,
        expected_version: int | None,
    ) -> DesktopApiResult[DocumentDto]:
        if self._document_api is None:
            return preview_error_result("Platform document API is not connected in this QML preview.")
        return self._document_api.update_document(
            DocumentUpdateCommand(
                document_id=document_id,
                is_active=not is_active,
                expected_version=expected_version,
            )
        )

    def _structure_lookup(self) -> dict[str, str]:
        if self._document_api is None:
            return {}
        result = self._document_api.list_document_structures(active_only=None)
        if not result.ok or result.data is None:
            return {}
        return {
            row.id: f"{row.structure_code} - {row.name}"
            for row in result.data
        }

    @staticmethod
    def _serialize_structure_option(row: DocumentStructureDto) -> dict[str, str]:
        return option_item(
            label=f"{row.structure_code} - {row.name}",
            value=row.id,
            supporting_text=title_case_code(row.default_document_type),
        )

    @staticmethod
    def _serialize_document(
        row: DocumentDto,
        *,
        structure_lookup: dict[str, str],
    ) -> PlatformWorkspaceActionItemViewModel:
        structure_label = structure_lookup.get(row.document_structure_id or "", "Unstructured")
        return PlatformWorkspaceActionItemViewModel(
            id=row.id,
            title=row.title,
            status_label="Active" if row.is_active else "Inactive",
            subtitle=f"{row.document_code} | {title_case_code(row.document_type)}",
            supporting_text=(
                f"{structure_label} | Version {row.business_version_label or '-'} | "
                f"{'Current' if row.is_current else 'Archived'}"
            ),
            meta_text=f"{title_case_code(row.storage_kind)} | {row.file_name or row.storage_uri or 'No file reference'}",
            can_primary_action=True,
            can_secondary_action=True,
            state={
                "id": row.id,
                "documentId": row.id,
                "documentCode": row.document_code,
                "title": row.title,
                "documentType": getattr(row.document_type, "value", row.document_type),
                "documentStructureId": row.document_structure_id or "",
                "storageKind": getattr(row.storage_kind, "value", row.storage_kind),
                "storageUri": row.storage_uri,
                "fileName": row.file_name,
                "mimeType": row.mime_type,
                "sourceSystem": row.source_system,
                "confidentialityLevel": row.confidentiality_level,
                "businessVersionLabel": row.business_version_label,
                "isCurrent": row.is_current,
                "notes": row.notes,
                "isActive": row.is_active,
                "version": row.version,
            },
        )


__all__ = ["PlatformDocumentCatalogPresenter"]
