from __future__ import annotations

from dataclasses import dataclass

from core.modules.maintenance_management.domain import MaintenanceWorkOrder, MaintenanceWorkRequest
from core.modules.maintenance_management.interfaces import (
    MaintenanceAssetRepository,
    MaintenanceLocationRepository,
    MaintenanceSystemRepository,
    MaintenanceWorkOrderRepository,
    MaintenanceWorkRequestRepository,
)
from core.platform.access.authorization import filter_scope_rows, require_scope_permission
from src.core.platform.auth.authorization import require_permission
from core.platform.common.exceptions import BusinessRuleError, NotFoundError, ValidationError
from core.platform.common.interfaces import OrganizationRepository, SiteRepository
from core.platform.documents import Document, DocumentIntegrationService, DocumentLink, DocumentStructure
from core.platform.documents.interfaces import (
    DocumentLinkRepository,
    DocumentRepository,
    DocumentStructureRepository,
)
from core.platform.org.domain import Organization


_MAINTENANCE_MODULE_CODE = "maintenance_management"
_SUPPORTED_ENTITY_TYPES = {
    "location",
    "system",
    "asset",
    "work_request",
    "work_order",
}


@dataclass(frozen=True)
class MaintenanceDocumentRecord:
    link_id: str
    document: Document
    structure: DocumentStructure | None
    entity_type: str
    entity_id: str
    entity_label: str
    site_id: str | None
    site_label: str
    link_role: str
    scope_anchor_id: str


class MaintenanceDocumentService:
    def __init__(
        self,
        *,
        document_repo: DocumentRepository,
        link_repo: DocumentLinkRepository,
        structure_repo: DocumentStructureRepository,
        document_integration_service: DocumentIntegrationService,
        organization_repo: OrganizationRepository,
        site_repo: SiteRepository,
        location_repo: MaintenanceLocationRepository,
        system_repo: MaintenanceSystemRepository,
        asset_repo: MaintenanceAssetRepository,
        work_request_repo: MaintenanceWorkRequestRepository,
        work_order_repo: MaintenanceWorkOrderRepository,
        user_session=None,
    ) -> None:
        self._document_repo = document_repo
        self._link_repo = link_repo
        self._structure_repo = structure_repo
        self._document_integration_service = document_integration_service
        self._organization_repo = organization_repo
        self._site_repo = site_repo
        self._location_repo = location_repo
        self._system_repo = system_repo
        self._asset_repo = asset_repo
        self._work_request_repo = work_request_repo
        self._work_order_repo = work_order_repo
        self._user_session = user_session

    def list_document_records(
        self,
        *,
        site_id: str | None = None,
        entity_type: str | None = None,
        active_only: bool | None = None,
        search_text: str = "",
    ) -> list[MaintenanceDocumentRecord]:
        self._require_read("list maintenance documents")
        organization = self._active_organization()
        normalized_entity_type = self._normalize_entity_type(entity_type, allow_blank=True)
        normalized_search = str(search_text or "").strip().lower()
        site_labels = self._site_labels()
        structures = self._structures_by_id(organization)
        links = self._link_repo.list_for_module(
            organization.id,
            _MAINTENANCE_MODULE_CODE,
            entity_type=normalized_entity_type,
        )
        rows: list[MaintenanceDocumentRecord] = []
        for link in links:
            document = self._document_repo.get(link.document_id)
            if document is None or document.organization_id != organization.id:
                continue
            if active_only is not None and document.is_active != bool(active_only):
                continue
            context = self._resolve_entity_context(link.entity_type, link.entity_id, organization)
            if context is None:
                continue
            if site_id is not None and context.site_id != site_id:
                continue
            structure = structures.get(document.document_structure_id or "")
            row = MaintenanceDocumentRecord(
                link_id=link.id,
                document=document,
                structure=structure,
                entity_type=link.entity_type,
                entity_id=link.entity_id,
                entity_label=context.entity_label,
                site_id=context.site_id,
                site_label=site_labels.get(context.site_id or "", context.site_id or "-"),
                link_role=link.link_role or "",
                scope_anchor_id=context.scope_anchor_id,
            )
            if normalized_search:
                haystack = " ".join(
                    [
                        row.document.document_code,
                        row.document.title,
                        row.document.file_name,
                        row.document.source_system,
                        row.entity_type,
                        row.entity_label,
                        row.link_role,
                        structure.structure_code if structure is not None else "",
                        structure.name if structure is not None else "",
                    ]
                ).lower()
                if normalized_search not in haystack:
                    continue
            rows.append(row)
        return filter_scope_rows(
            rows,
            self._user_session,
            scope_type="maintenance",
            permission_code="maintenance.read",
            scope_id_getter=lambda row: row.scope_anchor_id,
        )

    def list_documents_for_entity(
        self,
        *,
        entity_type: str,
        entity_id: str,
        active_only: bool | None = None,
    ) -> list[Document]:
        context = self._require_entity_context(
            entity_type,
            entity_id,
            operation_label="view maintenance documents",
        )
        self._require_scope_read(context.scope_anchor_id, operation_label="view maintenance documents")
        return self._document_integration_service.list_documents_for_entity(
            required_permission="maintenance.read",
            operation_label="view maintenance documents",
            module_code=_MAINTENANCE_MODULE_CODE,
            entity_type=context.entity_type,
            entity_id=context.entity_id,
            active_only=active_only,
        )

    def list_document_records_for_entity(
        self,
        *,
        entity_type: str,
        entity_id: str,
        active_only: bool | None = None,
    ) -> list[MaintenanceDocumentRecord]:
        context = self._require_entity_context(
            entity_type,
            entity_id,
            operation_label="view maintenance documents",
        )
        self._require_scope_read(context.scope_anchor_id, operation_label="view maintenance documents")
        organization = self._active_organization()
        site_labels = self._site_labels()
        structures = self._structures_by_id(organization)
        rows: list[MaintenanceDocumentRecord] = []
        for link in self._link_repo.list_for_entity(
            organization.id,
            _MAINTENANCE_MODULE_CODE,
            context.entity_type,
            context.entity_id,
        ):
            document = self._document_repo.get(link.document_id)
            if document is None or document.organization_id != organization.id:
                continue
            if active_only is not None and document.is_active != bool(active_only):
                continue
            rows.append(
                MaintenanceDocumentRecord(
                    link_id=link.id,
                    document=document,
                    structure=structures.get(document.document_structure_id or ""),
                    entity_type=context.entity_type,
                    entity_id=context.entity_id,
                    entity_label=context.entity_label,
                    site_id=context.site_id,
                    site_label=site_labels.get(context.site_id or "", context.site_id or "-"),
                    link_role=link.link_role or "",
                    scope_anchor_id=context.scope_anchor_id,
                )
            )
        return rows

    def list_document_structures(
        self,
        *,
        active_only: bool | None = True,
        object_scope: str | None = None,
    ) -> list[DocumentStructure]:
        self._require_read("list maintenance document structures")
        organization = self._active_organization()
        normalized_scope = str(object_scope or "").strip().upper() or None
        return self._structure_repo.list_for_organization(
            organization.id,
            active_only=active_only,
            object_scope=normalized_scope,
        )

    def list_links_for_document(self, document_id: str) -> list[DocumentLink]:
        self._require_read("view maintenance document links")
        organization = self._active_organization()
        document = self._document_repo.get(document_id)
        if document is None or document.organization_id != organization.id:
            raise NotFoundError("Document not found in the active organization.", code="DOCUMENT_NOT_FOUND")
        rows: list[DocumentLink] = []
        for link in self._link_repo.list_for_document(document.id):
            if link.module_code != _MAINTENANCE_MODULE_CODE:
                continue
            context = self._resolve_entity_context(link.entity_type, link.entity_id, organization)
            if context is None:
                continue
            if self._user_session is not None and context.scope_anchor_id:
                try:
                    require_scope_permission(
                        self._user_session,
                        "maintenance",
                        context.scope_anchor_id,
                        "maintenance.read",
                        operation_label="view maintenance document links",
                    )
                except BusinessRuleError:
                    continue
            rows.append(link)
        return rows

    def list_available_documents(
        self,
        *,
        active_only: bool | None = True,
        search_text: str = "",
    ) -> list[Document]:
        rows = self._document_integration_service.list_available_documents(
            required_permission="maintenance.read",
            operation_label="browse maintenance documents",
            active_only=active_only,
        )
        normalized_search = str(search_text or "").strip().lower()
        if not normalized_search:
            return rows
        return [
            row
            for row in rows
            if normalized_search
            in " ".join(
                [
                    row.document_code,
                    row.title,
                    row.file_name,
                    row.storage_uri,
                    row.source_system,
                    row.notes,
                ]
            ).lower()
        ]

    def list_entity_choices(
        self,
        *,
        entity_type: str,
        site_id: str | None = None,
    ) -> list[tuple[str, str]]:
        self._require_read("list maintenance document entities")
        organization = self._active_organization()
        normalized_entity_type = self._normalize_entity_type(entity_type)
        if normalized_entity_type == "location":
            rows = self._location_repo.list_for_organization(organization.id, active_only=None, site_id=site_id)
            return [(row.id, f"{row.location_code} - {row.name}") for row in rows]
        if normalized_entity_type == "system":
            rows = self._system_repo.list_for_organization(organization.id, active_only=None, site_id=site_id)
            return [(row.id, f"{row.system_code} - {row.name}") for row in rows]
        if normalized_entity_type == "asset":
            rows = self._asset_repo.list_for_organization(organization.id, active_only=None, site_id=site_id)
            return [(row.id, f"{row.asset_code} - {row.name}") for row in rows]
        if normalized_entity_type == "work_request":
            rows = self._work_request_repo.list_for_organization(organization.id, site_id=site_id)
            return [
                (
                    row.id,
                    f"{row.work_request_code} - {row.title or row.request_type.value.replace('_', ' ').title()}",
                )
                for row in rows
            ]
        rows = self._work_order_repo.list_for_organization(organization.id, site_id=site_id)
        return [
            (
                row.id,
                f"{row.work_order_code} - {row.title or row.work_order_type.value.replace('_', ' ').title()}",
            )
            for row in rows
        ]

    def link_existing_document(
        self,
        *,
        entity_type: str,
        entity_id: str,
        document_id: str,
        link_role: str = "reference",
    ) -> DocumentLink:
        context = self._require_entity_context(
            entity_type,
            entity_id,
            operation_label="link maintenance document",
        )
        self._require_scope_manage(context.scope_anchor_id, operation_label="link maintenance document")
        return self._document_integration_service.link_existing_document(
            required_permission="maintenance.manage",
            operation_label="link maintenance document",
            module_code=_MAINTENANCE_MODULE_CODE,
            entity_type=context.entity_type,
            entity_id=context.entity_id,
            document_id=document_id,
            link_role=link_role,
        )

    def register_entity_attachments(
        self,
        *,
        entity_type: str,
        entity_id: str,
        attachments: list[str] | None,
        document_type=None,
        document_structure_id: str | None = None,
        business_version_label: str = "",
        source_system: str = "maintenance",
        link_role: str = "evidence",
        notes: str = "",
    ) -> list[Document]:
        context = self._require_entity_context(
            entity_type,
            entity_id,
            operation_label="capture maintenance evidence",
        )
        self._require_scope_manage(context.scope_anchor_id, operation_label="capture maintenance evidence")
        return self._document_integration_service.register_entity_attachments(
            required_permission="maintenance.manage",
            operation_label="capture maintenance evidence",
            module_code=_MAINTENANCE_MODULE_CODE,
            entity_type=context.entity_type,
            entity_id=context.entity_id,
            attachments=attachments,
            document_type=document_type,
            document_structure_id=document_structure_id,
            business_version_label=business_version_label,
            source_system=source_system,
            link_role=link_role,
            notes=notes,
        )

    def unlink_document_link(self, link_id: str) -> None:
        self._require_manage("unlink maintenance document")
        organization = self._active_organization()
        link = self._link_repo.get(link_id)
        if link is None or link.module_code != _MAINTENANCE_MODULE_CODE or link.organization_id != organization.id:
            raise NotFoundError("Maintenance document link not found.", code="DOCUMENT_LINK_NOT_FOUND")
        context = self._require_entity_context(
            link.entity_type,
            link.entity_id,
            operation_label="unlink maintenance document",
        )
        self._require_scope_manage(context.scope_anchor_id, operation_label="unlink maintenance document")
        self._document_integration_service.unlink_existing_document(
            required_permission="maintenance.manage",
            operation_label="unlink maintenance document",
            module_code=_MAINTENANCE_MODULE_CODE,
            entity_type=context.entity_type,
            entity_id=context.entity_id,
            document_id=link.document_id,
            link_role=link.link_role or "reference",
        )

    def _require_entity_context(self, entity_type: str, entity_id: str, *, operation_label: str) -> "_EntityContext":
        self._require_read(operation_label)
        organization = self._active_organization()
        context = self._resolve_entity_context(entity_type, entity_id, organization)
        if context is None:
            raise NotFoundError("Maintenance document entity not found in the active organization.", code="MAINTENANCE_DOCUMENT_ENTITY_NOT_FOUND")
        return context

    def _resolve_entity_context(
        self,
        entity_type: str,
        entity_id: str,
        organization: Organization,
    ) -> "_EntityContext | None":
        normalized_entity_type = self._normalize_entity_type(entity_type)
        normalized_entity_id = str(entity_id or "").strip()
        if not normalized_entity_id:
            return None
        if normalized_entity_type == "location":
            row = self._location_repo.get(normalized_entity_id)
            if row is None or row.organization_id != organization.id:
                return None
            return _EntityContext(
                entity_type="location",
                entity_id=row.id,
                entity_label=f"{row.location_code} - {row.name}",
                site_id=row.site_id,
                scope_anchor_id=row.id,
            )
        if normalized_entity_type == "system":
            row = self._system_repo.get(normalized_entity_id)
            if row is None or row.organization_id != organization.id:
                return None
            return _EntityContext(
                entity_type="system",
                entity_id=row.id,
                entity_label=f"{row.system_code} - {row.name}",
                site_id=row.site_id,
                scope_anchor_id=row.id,
            )
        if normalized_entity_type == "asset":
            row = self._asset_repo.get(normalized_entity_id)
            if row is None or row.organization_id != organization.id:
                return None
            return _EntityContext(
                entity_type="asset",
                entity_id=row.id,
                entity_label=f"{row.asset_code} - {row.name}",
                site_id=row.site_id,
                scope_anchor_id=row.id,
            )
        if normalized_entity_type == "work_request":
            row = self._work_request_repo.get(normalized_entity_id)
            if row is None or row.organization_id != organization.id:
                return None
            return _EntityContext.from_work_request(row)
        row = self._work_order_repo.get(normalized_entity_id)
        if row is None or row.organization_id != organization.id:
            return None
        return _EntityContext.from_work_order(row)

    def _structures_by_id(self, organization: Organization) -> dict[str, DocumentStructure]:
        return {
            row.id: row
            for row in self._structure_repo.list_for_organization(organization.id, active_only=None)
        }

    def _site_labels(self) -> dict[str, str]:
        organization = self._active_organization()
        return {
            row.id: row.name
            for row in self._site_repo.list_for_organization(organization.id, active_only=None)
        }

    def _active_organization(self) -> Organization:
        organization = self._organization_repo.get_active()
        if organization is None:
            raise NotFoundError("Active organization not found.", code="ORGANIZATION_NOT_FOUND")
        return organization

    def _normalize_entity_type(self, entity_type: str | None, *, allow_blank: bool = False) -> str | None:
        normalized = str(entity_type or "").strip().lower()
        if allow_blank and not normalized:
            return None
        if normalized not in _SUPPORTED_ENTITY_TYPES:
            raise ValidationError(
                "Unsupported maintenance document entity type.",
                code="MAINTENANCE_DOCUMENT_ENTITY_TYPE_INVALID",
            )
        return normalized

    def _require_read(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.read", operation_label=operation_label)

    def _require_manage(self, operation_label: str) -> None:
        require_permission(self._user_session, "maintenance.manage", operation_label=operation_label)

    def _require_scope_read(self, scope_id: str, *, operation_label: str) -> None:
        if scope_id:
            require_scope_permission(
                self._user_session,
                "maintenance",
                scope_id,
                "maintenance.read",
                operation_label=operation_label,
            )
            return
        if self._user_session is not None and self._user_session.is_scope_restricted("maintenance"):
            raise BusinessRuleError(
                f"Permission denied for {operation_label}. The record is not anchored to a maintenance scope grant.",
                code="PERMISSION_DENIED",
            )

    def _require_scope_manage(self, scope_id: str, *, operation_label: str) -> None:
        if scope_id:
            require_scope_permission(
                self._user_session,
                "maintenance",
                scope_id,
                "maintenance.manage",
                operation_label=operation_label,
            )
            return
        if self._user_session is not None and self._user_session.is_scope_restricted("maintenance"):
            raise BusinessRuleError(
                f"Permission denied for {operation_label}. The record is not anchored to a maintenance scope grant.",
                code="PERMISSION_DENIED",
            )


@dataclass(frozen=True)
class _EntityContext:
    entity_type: str
    entity_id: str
    entity_label: str
    site_id: str | None
    scope_anchor_id: str

    @staticmethod
    def from_work_request(row: MaintenanceWorkRequest) -> "_EntityContext":
        return _EntityContext(
            entity_type="work_request",
            entity_id=row.id,
            entity_label=f"{row.work_request_code} - {row.title or row.request_type.value.replace('_', ' ').title()}",
            site_id=row.site_id,
            scope_anchor_id=row.asset_id or row.system_id or row.location_id or "",
        )

    @staticmethod
    def from_work_order(row: MaintenanceWorkOrder) -> "_EntityContext":
        return _EntityContext(
            entity_type="work_order",
            entity_id=row.id,
            entity_label=f"{row.work_order_code} - {row.title or row.work_order_type.value.replace('_', ' ').title()}",
            site_id=row.site_id,
            scope_anchor_id=row.asset_id or row.system_id or row.location_id or "",
        )


__all__ = ["MaintenanceDocumentRecord", "MaintenanceDocumentService"]
