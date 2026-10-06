from __future__ import annotations

from typing import Any

from src.core.platform.api.desktop.master_data.documents.document import (
    PlatformDocumentDesktopApi,
)
from src.core.platform.api.desktop.master_data.employee.employee import (
    PlatformEmployeeDesktopApi,
)
from src.core.platform.api.desktop.master_data.documents.models.document import (
    DocumentCreateCommand,
    DocumentDto,
)
from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.platform.domain.master_data.documents import DocumentType
from src.ui_qml.platform.presenters.common.presenter_support_helpers import (
    option_item,
    preview_error_result,
    string_value,
    title_case_code,
)
from src.ui_qml.platform.view_models import (
    PlatformWorkspaceActionItemViewModel,
    PlatformWorkspaceActionListViewModel,
)

# Document lifecycle is a plain boolean (is_active) -- mirrors the tone map
# already established in document_catalog_presenter.py; kept as its own
# copy rather than a shared import since the two presenters serialize
# different row shapes and have no other coupling.
_DOCUMENT_STATUS_TONE = {True: "success", False: "neutral"}


def _document_status_label(is_active: bool) -> dict[str, str]:
    return {"label": "Active" if is_active else "Inactive", "tone": _DOCUMENT_STATUS_TONE[is_active]}


class PlatformEmployeeDocumentsPresenter:
    """Employee Documents -- the first real production consumer of the
    generic Platform DocumentLink capability. Every call here takes an
    explicit employee_id; the generic entity_type="employee" translation
    happens beneath this boundary (EmployeeService/employee_documents.py),
    never in QML or this presenter."""

    def __init__(
        self,
        *,
        employee_api: PlatformEmployeeDesktopApi | None = None,
        document_api: PlatformDocumentDesktopApi | None = None,
    ) -> None:
        self._employee_api = employee_api
        # Only used to build the "Link Existing Document" picker's option
        # list (every active Document in the organization) and to create a
        # brand-new Document before linking it -- never to read/write
        # Employee state, and never bypasses DocumentService's own
        # central authorization (both calls go through the same desktop
        # API every other Document consumer uses).
        self._document_api = document_api

    def build_documents_page(
        self,
        employee_id: str,
        *,
        page: int = 1,
        page_size: int = 25,
        search: str = "",
        status: str = "",
        document_type: str = "",
    ) -> PlatformWorkspaceActionListViewModel:
        if self._employee_api is None:
            return PlatformWorkspaceActionListViewModel(
                title="Documents",
                subtitle="Documents appear here once the platform employee API is connected.",
                empty_state="Platform employee API is not connected in this QML preview.",
                paginated=True,
                page=page,
                page_size=page_size,
            )
        active_only: bool | None
        if status == "active":
            active_only = True
        elif status == "inactive":
            active_only = False
        else:
            active_only = None

        result = self._employee_api.list_employee_documents_page(
            employee_id, page=page, page_size=page_size, search=search,
            active_only=active_only, document_type=document_type or None,
        )
        if not result.ok or result.data is None:
            message = result.error.message if result.error is not None else "Unable to load documents."
            return PlatformWorkspaceActionListViewModel(
                title="Documents",
                subtitle=message,
                empty_state=message,
                paginated=True,
                page=page,
                page_size=page_size,
            )

        document_page = result.data
        return PlatformWorkspaceActionListViewModel(
            title="Documents",
            subtitle="Documents associated with this employee.",
            empty_state="No documents linked to this employee.",
            no_results_state="No documents match your current filters.",
            items=tuple(self._serialize_document(row) for row in document_page.items),
            paginated=True,
            page=document_page.page,
            page_size=document_page.page_size,
            total_count=document_page.total,
            filtered_total=document_page.filtered_total,
        )

    def link_document(self, employee_id: str, document_id: str) -> DesktopApiResult[object]:
        if self._employee_api is None:
            return preview_error_result("Platform employee API is not connected in this QML preview.")
        return self._employee_api.link_employee_document(employee_id, document_id)

    def unlink_document(self, employee_id: str, link_id: str) -> DesktopApiResult[object]:
        if self._employee_api is None:
            return preview_error_result("Platform employee API is not connected in this QML preview.")
        return self._employee_api.unlink_employee_document(employee_id, link_id)

    def build_document_type_options(self) -> tuple[dict[str, str], ...]:
        return tuple(
            option_item(label=title_case_code(document_type), value=document_type.value)
            for document_type in DocumentType
        )

    def build_document_options(self) -> tuple[dict[str, str], ...]:
        """Every active Document in the organization, for the "Link
        Existing Document" picker -- a plain option list (mirrors how
        Department's own Create/Edit dialog picks Site/Parent/HOD), not a
        searchable paginated browser; organizations with very large
        Document catalogs may need a real search-as-you-type picker later,
        but no such need has been confirmed yet for this first vertical
        slice."""
        if self._document_api is None:
            return ()
        result = self._document_api.list_documents(active_only=True)
        if not result.ok or result.data is None:
            return ()
        return tuple(
            option_item(label=row.title, value=row.id, supporting_text=row.document_code)
            for row in result.data
        )

    def create_and_link_document(self, employee_id: str, payload: dict[str, Any]) -> DesktopApiResult[object]:
        """"Add Document" / create-new flow -- creates a brand-new Document
        record then links it to this Employee. Not a single atomic
        transaction (create_document and add_link are each their own
        DocumentService-owned unit of work), but failure after a successful
        create never silently loses the Document -- it simply remains
        unlinked and can be linked via "Link Existing Document" afterward."""
        if self._document_api is None or self._employee_api is None:
            return preview_error_result("Platform document API is not connected in this QML preview.")
        create_result = self._document_api.create_document(
            DocumentCreateCommand(
                document_code=string_value(payload, "documentCode"),
                title=string_value(payload, "title"),
                document_type=string_value(payload, "documentType", default="GENERAL"),
                storage_uri=string_value(payload, "storageUri"),
            )
        )
        if not create_result.ok or create_result.data is None:
            return create_result
        return self._employee_api.link_employee_document(employee_id, create_result.data.id)

    @staticmethod
    def _serialize_document(row: DocumentDto) -> PlatformWorkspaceActionItemViewModel:
        return PlatformWorkspaceActionItemViewModel(
            id=row.id,
            title=row.title,
            status_label=_document_status_label(row.is_active),
            subtitle=f"{row.document_code} | {title_case_code(row.document_type)}",
            supporting_text=f"Version {row.business_version_label or '-'}",
            meta_text=row.uploaded_at.strftime("%d %b %Y") if row.uploaded_at else "-",
            can_primary_action=True,
            can_secondary_action=True,
            state={
                "id": row.id,
                "documentId": row.id,
                "linkId": row.link_id,
                "documentCode": row.document_code,
                "title": row.title,
                "documentType": getattr(row.document_type, "value", row.document_type),
                "businessVersionLabel": row.business_version_label or "",
                "isActive": row.is_active,
                # There is no real `updated_at` field on Document today
                # (only `uploaded_at`, the original upload timestamp) --
                # exposed honestly as "uploadedAt" rather than inventing an
                # "updatedAt" the domain doesn't actually track. Formatted
                # (not raw ISO) since this is a default-visible column.
                "uploadedAt": row.uploaded_at.strftime("%d %b %Y") if row.uploaded_at else "-",
            },
        )


__all__ = ["PlatformEmployeeDocumentsPresenter"]
