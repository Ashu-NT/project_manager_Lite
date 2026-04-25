from __future__ import annotations

from pathlib import Path
from typing import Any

from src.api.desktop.platform import (
    DocumentDto,
    DocumentLinkCreateCommand,
    DocumentLinkDto,
    DocumentStructureCreateCommand,
    DocumentStructureDto,
    DocumentStructureUpdateCommand,
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


_OBJECT_SCOPE_CHOICES = (
    "GENERAL",
    "ASSET",
    "SYSTEM",
    "WORK_ORDER",
    "TASK_TEMPLATE",
    "EMPLOYEE",
    "INSPECTION",
    "REPORT",
    "INVENTORY_ITEM",
    "STOREROOM",
    "SITE",
    "DEPARTMENT",
)


class PlatformDocumentManagementPresenter:
    def __init__(self, *, document_api: PlatformDocumentDesktopApi | None = None) -> None:
        self._document_api = document_api

    def build_structure_management(
        self,
    ) -> tuple[PlatformWorkspaceActionListViewModel, dict[str, object]]:
        if self._document_api is None:
            return (
                PlatformWorkspaceActionListViewModel(
                    title="Document Structures",
                    subtitle="Shared structure governance appears here once the platform document API is connected.",
                    empty_state="Platform document API is not connected in this QML preview.",
                ),
                self._empty_structure_editor_options(),
            )

        result = self._document_api.list_document_structures(active_only=None)
        if not result.ok or result.data is None:
            message = (
                result.error.message
                if result.error is not None
                else "Unable to load document structures."
            )
            return (
                PlatformWorkspaceActionListViewModel(
                    title="Document Structures",
                    subtitle=message,
                    empty_state=message,
                ),
                self._empty_structure_editor_options(),
            )

        rows = tuple(result.data)
        parent_lookup = {row.id: row for row in rows}
        catalog = PlatformWorkspaceActionListViewModel(
            title="Document Structures",
            subtitle="Shared taxonomy for policies, procedures, certificates, drawings, and governed records.",
            empty_state="No document structures are available yet.",
            items=tuple(
                self._serialize_structure(row, parent_lookup=parent_lookup)
                for row in rows
            ),
        )
        return (catalog, self._serialize_structure_editor_options(rows))

    def build_document_focus(
        self,
        preferred_document_id: str | None,
    ) -> tuple[str, dict[str, object], dict[str, object], PlatformWorkspaceActionListViewModel]:
        if self._document_api is None:
            return (
                "",
                self._empty_document_detail(),
                self._empty_preview_state(),
                PlatformWorkspaceActionListViewModel(
                    title="Linked Records",
                    subtitle="Document links appear here once the platform document API is connected.",
                    empty_state="Platform document API is not connected in this QML preview.",
                ),
            )

        documents_result = self._document_api.list_documents(active_only=None)
        if not documents_result.ok or documents_result.data is None:
            message = (
                documents_result.error.message
                if documents_result.error is not None
                else "Unable to load documents."
            )
            return (
                "",
                self._empty_document_detail(summary=message),
                self._empty_preview_state(summary=message),
                PlatformWorkspaceActionListViewModel(
                    title="Linked Records",
                    subtitle=message,
                    empty_state=message,
                ),
            )

        document_rows = tuple(documents_result.data)
        selected_document = self._resolve_selected_document(
            rows=document_rows,
            preferred_document_id=preferred_document_id,
        )
        if selected_document is None:
            return (
                "",
                self._empty_document_detail(),
                self._empty_preview_state(),
                PlatformWorkspaceActionListViewModel(
                    title="Linked Records",
                    subtitle="Select a document to review its linked business records.",
                    empty_state="Select a document to manage links.",
                ),
            )

        structures_result = self._document_api.list_document_structures(active_only=None)
        structure_rows = tuple(
            structures_result.data
            if structures_result.ok and structures_result.data is not None
            else ()
        )
        structure_lookup = {row.id: row for row in structure_rows}

        links_result = self._document_api.list_links(selected_document.id)
        if links_result.ok and links_result.data is not None:
            link_rows = tuple(links_result.data)
            link_catalog = PlatformWorkspaceActionListViewModel(
                title="Linked Records",
                subtitle=f"Cross-module references attached to {selected_document.document_code}.",
                empty_state="No linked records yet.",
                items=tuple(self._serialize_link(row) for row in link_rows),
            )
        else:
            link_rows = ()
            message = (
                links_result.error.message
                if links_result.error is not None
                else "Unable to load linked records."
            )
            link_catalog = PlatformWorkspaceActionListViewModel(
                title="Linked Records",
                subtitle=message,
                empty_state=message,
            )

        preview = self._serialize_preview_state(selected_document)
        detail = self._serialize_document_detail(
            selected_document,
            structure_lookup=structure_lookup,
            link_rows=link_rows,
            preview_status=preview["statusLabel"],
        )
        return (selected_document.id, detail, preview, link_catalog)

    def create_document_structure(
        self,
        payload: dict[str, Any],
    ) -> DesktopApiResult[DocumentStructureDto]:
        if self._document_api is None:
            return preview_error_result("Platform document API is not connected in this QML preview.")
        return self._document_api.create_document_structure(
            DocumentStructureCreateCommand(
                structure_code=string_value(payload, "structureCode"),
                name=string_value(payload, "name"),
                description=string_value(payload, "description"),
                parent_structure_id=optional_string_value(payload, "parentStructureId"),
                object_scope=string_value(payload, "objectScope", default="GENERAL"),
                default_document_type=string_value(
                    payload,
                    "defaultDocumentType",
                    default=DocumentType.GENERAL.value,
                ),
                sort_order=int_value(payload, "sortOrder") or 0,
                is_active=bool_value(payload, "isActive", default=True),
                notes=string_value(payload, "notes"),
            )
        )

    def update_document_structure(
        self,
        payload: dict[str, Any],
    ) -> DesktopApiResult[DocumentStructureDto]:
        if self._document_api is None:
            return preview_error_result("Platform document API is not connected in this QML preview.")
        return self._document_api.update_document_structure(
            DocumentStructureUpdateCommand(
                structure_id=string_value(payload, "structureId"),
                structure_code=string_value(payload, "structureCode"),
                name=string_value(payload, "name"),
                description=string_value(payload, "description"),
                parent_structure_id=optional_string_value(payload, "parentStructureId"),
                object_scope=string_value(payload, "objectScope", default="GENERAL"),
                default_document_type=string_value(
                    payload,
                    "defaultDocumentType",
                    default=DocumentType.GENERAL.value,
                ),
                sort_order=int_value(payload, "sortOrder") or 0,
                is_active=bool_value(payload, "isActive", default=True),
                notes=string_value(payload, "notes"),
                expected_version=int_value(payload, "expectedVersion"),
            )
        )

    def toggle_document_structure_active(
        self,
        *,
        structure_id: str,
        is_active: bool,
        expected_version: int | None,
    ) -> DesktopApiResult[DocumentStructureDto]:
        if self._document_api is None:
            return preview_error_result("Platform document API is not connected in this QML preview.")
        return self._document_api.update_document_structure(
            DocumentStructureUpdateCommand(
                structure_id=structure_id,
                is_active=not is_active,
                expected_version=expected_version,
            )
        )

    def add_document_link(
        self,
        payload: dict[str, Any],
    ) -> DesktopApiResult[DocumentLinkDto]:
        if self._document_api is None:
            return preview_error_result("Platform document API is not connected in this QML preview.")
        return self._document_api.add_link(
            DocumentLinkCreateCommand(
                document_id=string_value(payload, "documentId"),
                module_code=string_value(payload, "moduleCode"),
                entity_type=string_value(payload, "entityType"),
                entity_id=string_value(payload, "entityId"),
                link_role=string_value(payload, "linkRole"),
            )
        )

    def remove_document_link(self, link_id: str) -> DesktopApiResult[None]:
        if self._document_api is None:
            return preview_error_result("Platform document API is not connected in this QML preview.")
        return self._document_api.remove_link(link_id.strip())

    @staticmethod
    def _resolve_selected_document(
        *,
        rows: tuple[DocumentDto, ...],
        preferred_document_id: str | None,
    ) -> DocumentDto | None:
        normalized_id = str(preferred_document_id or "").strip()
        if normalized_id:
            for row in rows:
                if row.id == normalized_id:
                    return row
        return rows[0] if rows else None

    @staticmethod
    def _serialize_structure_editor_options(
        rows: tuple[DocumentStructureDto, ...],
    ) -> dict[str, object]:
        return {
            "parentOptions": [
                option_item(
                    label=f"{row.structure_code} - {row.name}",
                    value=row.id,
                    supporting_text=title_case_code(row.object_scope),
                )
                for row in rows
            ],
            "objectScopeOptions": [
                option_item(
                    label=title_case_code(scope_code),
                    value=scope_code,
                )
                for scope_code in _OBJECT_SCOPE_CHOICES
            ],
            "defaultTypeOptions": [
                option_item(
                    label=title_case_code(document_type),
                    value=document_type.value,
                )
                for document_type in DocumentType
            ],
        }

    @staticmethod
    def _serialize_structure(
        row: DocumentStructureDto,
        *,
        parent_lookup: dict[str, DocumentStructureDto],
    ) -> PlatformWorkspaceActionItemViewModel:
        parent = parent_lookup.get(row.parent_structure_id or "")
        return PlatformWorkspaceActionItemViewModel(
            id=row.id,
            title=row.name,
            status_label="Active" if row.is_active else "Inactive",
            subtitle=f"{row.structure_code} | {title_case_code(row.object_scope)}",
            supporting_text=(
                f"Default type: {title_case_code(row.default_document_type)} | "
                f"Parent: {parent.name if parent is not None else 'Top level'}"
            ),
            meta_text=f"Sort order: {row.sort_order}",
            can_primary_action=True,
            can_secondary_action=True,
            state={
                "id": row.id,
                "structureId": row.id,
                "structureCode": row.structure_code,
                "name": row.name,
                "description": row.description,
                "parentStructureId": row.parent_structure_id or "",
                "objectScope": row.object_scope,
                "defaultDocumentType": getattr(
                    row.default_document_type,
                    "value",
                    row.default_document_type,
                ),
                "sortOrder": row.sort_order,
                "isActive": row.is_active,
                "notes": row.notes,
                "version": row.version,
            },
        )

    @staticmethod
    def _serialize_link(row: DocumentLinkDto) -> PlatformWorkspaceActionItemViewModel:
        role_label = title_case_code(row.link_role) if str(row.link_role or "").strip() else "Linked"
        return PlatformWorkspaceActionItemViewModel(
            id=row.id,
            title=f"{row.module_code} / {row.entity_type}",
            status_label=role_label,
            subtitle=row.entity_id,
            supporting_text=f"Role: {row.link_role or 'not set'}",
            meta_text=f"Document: {row.document_id}",
            can_secondary_action=True,
            state={
                "id": row.id,
                "linkId": row.id,
                "documentId": row.document_id,
                "moduleCode": row.module_code,
                "entityType": row.entity_type,
                "entityId": row.entity_id,
                "linkRole": row.link_role,
            },
        )

    def _serialize_document_detail(
        self,
        row: DocumentDto,
        *,
        structure_lookup: dict[str, DocumentStructureDto],
        link_rows: tuple[DocumentLinkDto, ...],
        preview_status: str,
    ) -> dict[str, object]:
        structure = structure_lookup.get(row.document_structure_id or "")
        structure_label = (
            f"{structure.structure_code} - {structure.name}"
            if structure is not None
            else "Unstructured"
        )
        return {
            "hasSelection": True,
            "documentId": row.id,
            "title": row.title,
            "summary": (
                f"{row.document_code} | {title_case_code(row.document_type)} | "
                f"{structure_label} | {'Active' if row.is_active else 'Inactive'} | "
                f"{len(link_rows)} linked records"
            ),
            "badges": [
                {"label": "Type", "value": title_case_code(row.document_type)},
                {"label": "Storage", "value": title_case_code(row.storage_kind)},
                {"label": "Preview", "value": preview_status},
                {"label": "Links", "value": str(len(link_rows))},
            ],
            "metadataRows": [
                {"label": "Code", "value": row.document_code or "-"},
                {"label": "Structure", "value": structure_label},
                {"label": "File name", "value": row.file_name or "-"},
                {"label": "MIME type", "value": row.mime_type or "-"},
                {"label": "Version / revision", "value": row.business_version_label or "-"},
                {"label": "Source system", "value": row.source_system or "-"},
                {"label": "Confidentiality", "value": row.confidentiality_level or "-"},
                {"label": "Storage URI", "value": row.storage_uri or "-"},
            ],
            "notes": row.notes or "",
        }

    def _serialize_preview_state(self, row: DocumentDto) -> dict[str, object]:
        storage_kind = str(getattr(row.storage_kind, "value", row.storage_kind) or "").strip()
        storage_uri = str(row.storage_uri or "").strip()
        mime_type = str(row.mime_type or "").strip().lower()

        if storage_kind == DocumentStorageKind.FILE_PATH.value:
            candidate = Path(storage_uri).expanduser() if storage_uri else None
            if candidate is None or not candidate.exists() or not candidate.is_file():
                return {
                    "statusLabel": "Local file missing",
                    "summary": (
                        "The record points to a local file path, but that file is not available on this runtime."
                    ),
                    "canOpen": False,
                    "openLabel": "Open File",
                    "openTargetUrl": "",
                }
            if candidate.suffix.lower() == ".pdf" or mime_type == "application/pdf":
                return {
                    "statusLabel": "PDF available",
                    "summary": "This local PDF can be opened from the document workspace.",
                    "canOpen": True,
                    "openLabel": "Open PDF",
                    "openTargetUrl": candidate.resolve().as_uri(),
                }
            return {
                "statusLabel": "File available",
                "summary": "This local document can be opened in the default desktop viewer.",
                "canOpen": True,
                "openLabel": "Open File",
                "openTargetUrl": candidate.resolve().as_uri(),
            }

        if storage_kind == DocumentStorageKind.EXTERNAL_URL.value:
            return {
                "statusLabel": "Browser-linked",
                "summary": "This document is hosted at an external URL and can be opened in the browser.",
                "canOpen": bool(storage_uri),
                "openLabel": "Open URL",
                "openTargetUrl": storage_uri,
            }

        return {
            "statusLabel": "Metadata reference",
            "summary": (
                "This record is a governed metadata reference. The platform stores the catalog entry and business links,"
                " while the source system remains the document host."
            ),
            "canOpen": False,
            "openLabel": "Open Source",
            "openTargetUrl": "",
        }

    @staticmethod
    def _empty_document_detail(*, summary: str | None = None) -> dict[str, object]:
        return {
            "hasSelection": False,
            "documentId": "",
            "title": "Select a document",
            "summary": summary
            or "Choose a document to review its metadata, preview state, structures, and linked records.",
            "badges": [],
            "metadataRows": [],
            "notes": "",
        }

    @staticmethod
    def _empty_preview_state(*, summary: str | None = None) -> dict[str, object]:
        return {
            "statusLabel": "No document selected",
            "summary": summary
            or "Select a document to inspect its preview status and open target.",
            "canOpen": False,
            "openLabel": "Open Source",
            "openTargetUrl": "",
        }

    @staticmethod
    def _empty_structure_editor_options() -> dict[str, object]:
        return {
            "parentOptions": [],
            "objectScopeOptions": [],
            "defaultTypeOptions": [],
        }


__all__ = ["PlatformDocumentManagementPresenter"]
