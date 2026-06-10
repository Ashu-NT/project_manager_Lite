from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.shared.models.data_table_model import DynamicTableModel
from src.ui_qml.modules.project_management.controllers.common import (
    ProjectManagementWorkspaceControllerBase,
    serialize_resource_availability_view_model,
    serialize_resource_catalog_overview_view_model,
    serialize_resource_detail_view_model,
    serialize_resource_employee_option_view_models,
    serialize_resource_record_view_models,
    serialize_selector_options,
    serialize_workspace_view_model,
)
from src.ui_qml.modules.project_management.presenters import (
    ProjectManagementWorkspacePresenter,
    ProjectResourcesWorkspacePresenter,
)

from .resource_state import (
    default_overview,
    default_resource_availability,
    default_resources,
    default_selected_resource,
)
from .resource_table_models import ResourceTableModels, create_resource_table_models
from .resource_state_setters import ResourceStateSettersMixin
from .resource_domain_event_binder import bind_resource_domain_events
from .resource_selection_handler import (
    activate_resource,
    select_resource,
    set_active_filter,
    set_category_filter,
    set_resource_page,
    set_resource_page_size,
    set_search_text,
)
from .resource_bulk_handler import (
    bulk_delete_resources,
    clear_resource_bulk_selection,
    select_visible_resources,
    set_resource_bulk_selection,
)
from .resource_mutation_handler import (
    create_resource,
    delete_resource,
    generate_entity_code,
    toggle_resource_active,
    update_resource,
)
from .resource_skills_handler import (
    add_certification,
    add_skill,
    load_skills_and_certs,
    reload_skills_and_certs,
    remove_certification,
    remove_skill,
)
from .resource_assignments_handler import load_resource_assignments
from .resource_export_handler import export_resources

QML_IMPORT_NAME = "ProjectManagement.Controllers"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
@QmlUncreatable("Project management workspace controllers are provided by the shell runtime.")
class ProjectManagementResourcesWorkspaceController(
    ResourceStateSettersMixin, ProjectManagementWorkspaceControllerBase
):
    overviewChanged = Signal()
    workerTypeOptionsChanged = Signal()
    categoryOptionsChanged = Signal()
    employeeOptionsChanged = Signal()
    selectedActiveFilterChanged = Signal()
    selectedCategoryFilterChanged = Signal()
    searchTextChanged = Signal()
    resourcesChanged = Signal()
    selectedResourceChanged = Signal()
    selectedResourceIdChanged = Signal()
    resourcePageChanged = Signal()
    resourcePageSizeChanged = Signal()
    resourceTotalCountChanged = Signal()
    selectedResourceIdsChanged = Signal()
    selectedResourceCountChanged = Signal()
    resourceSkillsChanged = Signal()
    resourceCertificationsChanged = Signal()
    resourceAvailabilityChanged = Signal()
    resourceAssignmentsChanged = Signal()

    def __init__(
        self,
        *,
        workspace_presenter: ProjectManagementWorkspacePresenter | None = None,
        resources_workspace_presenter: ProjectResourcesWorkspacePresenter | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._workspace_presenter = workspace_presenter or ProjectManagementWorkspacePresenter(
            "project_management.resources"
        )
        self._resources_workspace_presenter = (
            resources_workspace_presenter or ProjectResourcesWorkspacePresenter()
        )
        self._overview: dict[str, object] = default_overview()
        self._worker_type_options: list[dict[str, object]] = []
        self._category_options: list[dict[str, object]] = []
        self._employee_options: list[dict[str, object]] = []
        self._selected_active_filter = "all"
        self._selected_category_filter = "all"
        self._search_text = ""
        self._table_models: ResourceTableModels = create_resource_table_models(self)
        self._resources: dict[str, object] = default_resources()
        self._selected_resource: dict[str, object] = default_selected_resource()
        self._selected_resource_id = ""
        self._resource_page = 1
        self._resource_page_size = 25
        self._resource_total_count = 0
        self._selected_resource_ids: list[str] = []
        self._selected_resource_count = 0
        self._resource_skills: list[dict[str, object]] = []
        self._resource_certifications: list[dict[str, object]] = []
        self._resource_assignments: list[dict[str, object]] = []
        self._resource_availability: dict[str, object] = default_resource_availability()

        bind_resource_domain_events(self)
        self.refresh()

    # ── Properties ───────────────────────────────────────────────────────

    @Property("QVariantMap", notify=overviewChanged)
    def overview(self) -> dict[str, object]:
        return self._overview

    @Property("QVariantList", notify=workerTypeOptionsChanged)
    def workerTypeOptions(self) -> list[dict[str, object]]:
        return self._worker_type_options

    @Property("QVariantList", notify=categoryOptionsChanged)
    def categoryOptions(self) -> list[dict[str, object]]:
        return self._category_options

    @Property("QVariantList", notify=employeeOptionsChanged)
    def employeeOptions(self) -> list[dict[str, object]]:
        return self._employee_options

    @Property(str, notify=selectedActiveFilterChanged)
    def selectedActiveFilter(self) -> str:
        return self._selected_active_filter

    @Property(str, notify=selectedCategoryFilterChanged)
    def selectedCategoryFilter(self) -> str:
        return self._selected_category_filter

    @Property(str, notify=searchTextChanged)
    def searchText(self) -> str:
        return self._search_text

    @Property("QVariantMap", notify=resourcesChanged)
    def resources(self) -> dict[str, object]:
        return self._resources

    @Property(QObject, constant=True)
    def resourcesTableModel(self) -> DynamicTableModel:
        return self._table_models.resources

    @Property("QVariantMap", notify=selectedResourceChanged)
    def selectedResource(self) -> dict[str, object]:
        return self._selected_resource

    @Property(str, notify=selectedResourceIdChanged)
    def selectedResourceId(self) -> str:
        return self._selected_resource_id

    @Property(int, notify=resourcePageChanged)
    def resourcePage(self) -> int:
        return self._resource_page

    @Property(int, notify=resourcePageSizeChanged)
    def resourcePageSize(self) -> int:
        return self._resource_page_size

    @Property(int, notify=resourceTotalCountChanged)
    def resourceTotalCount(self) -> int:
        return self._resource_total_count

    @Property("QVariantList", notify=selectedResourceIdsChanged)
    def selectedResourceIds(self) -> list[str]:
        return list(self._selected_resource_ids)

    @Property(int, notify=selectedResourceCountChanged)
    def selectedResourceCount(self) -> int:
        return self._selected_resource_count

    @Property("QVariantList", notify=resourceSkillsChanged)
    def resourceSkills(self) -> list[dict[str, object]]:
        return list(self._resource_skills)

    @Property("QVariantList", notify=resourceCertificationsChanged)
    def resourceCertifications(self) -> list[dict[str, object]]:
        return list(self._resource_certifications)

    @Property(QObject, constant=True)
    def resourceSkillsTableModel(self) -> DynamicTableModel:
        return self._table_models.resource_skills

    @Property(QObject, constant=True)
    def resourceCertificationsTableModel(self) -> DynamicTableModel:
        return self._table_models.resource_certifications

    @Property(QObject, constant=True)
    def resourceAssignmentsTableModel(self) -> DynamicTableModel:
        return self._table_models.resource_assignments

    @Property("QVariantList", notify=resourceAssignmentsChanged)
    def resourceAssignments(self) -> list[dict[str, object]]:
        return list(self._resource_assignments)

    @Property("QVariantMap", notify=resourceAvailabilityChanged)
    def resourceAvailability(self) -> dict[str, object]:
        return self._resource_availability

    # ── Core ─────────────────────────────────────────────────────────────

    @Slot()
    def refresh(self) -> None:
        self._set_is_loading(True)
        try:
            self._set_error_message("")
            self._set_feedback_message("")
            self._set_workspace(
                serialize_workspace_view_model(
                    self._workspace_presenter.build_view_model()
                )
            )
            workspace_state = self._resources_workspace_presenter.build_workspace_state(
                search_text=self._search_text,
                active_filter=self._selected_active_filter,
                category_filter=self._selected_category_filter,
                selected_resource_id=self._selected_resource_id or None,
                page=self._resource_page,
                page_size=self._resource_page_size,
            )
            self._set_overview(
                serialize_resource_catalog_overview_view_model(workspace_state.overview)
            )
            self._set_worker_type_options(
                serialize_selector_options(workspace_state.worker_type_options)
            )
            self._set_category_options(
                serialize_selector_options(workspace_state.category_options)
            )
            self._set_employee_options(
                serialize_resource_employee_option_view_models(workspace_state.employee_options)
            )
            self._set_selected_active_filter(workspace_state.selected_active_filter)
            self._set_selected_category_filter(workspace_state.selected_category_filter)
            self._set_search_text(workspace_state.search_text)
            self._set_resources(
                {
                    "title": "Resource Pool",
                    "subtitle": "Manage resource capacity, staffing type, and active availability.",
                    "emptyState": workspace_state.empty_state,
                    "items": serialize_resource_record_view_models(workspace_state.resources),
                }
            )
            self._set_selected_resource_id(workspace_state.selected_resource_id)
            self._set_selected_resource(
                serialize_resource_detail_view_model(workspace_state.selected_resource_detail)
            )
            self._set_empty_state(workspace_state.empty_state)
            self._set_resource_total_count(workspace_state.total_count)
            self._set_resource_page(workspace_state.page)
            self._set_resource_page_size(workspace_state.page_size)
            self._set_resource_availability(
                serialize_resource_availability_view_model(workspace_state.resource_availability)
            )
            reload_skills_and_certs(self, workspace_state.selected_resource_id)
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._set_error_message(str(exc))
        finally:
            self._set_is_loading(False)

    # ── Filter / Selection ───────────────────────────────────────────────

    @Slot(str)
    def setSearchText(self, search_text: str) -> None:
        set_search_text(self, search_text)

    @Slot(str)
    def setActiveFilter(self, active_filter: str) -> None:
        set_active_filter(self, active_filter)

    @Slot(str)
    def setCategoryFilter(self, category_filter: str) -> None:
        set_category_filter(self, category_filter)

    @Slot(str)
    def selectResource(self, resource_id: str) -> None:
        select_resource(self, resource_id)

    @Slot(str)
    def activateResource(self, resource_id: str) -> None:
        activate_resource(self, resource_id)

    @Slot(str)
    def loadSkillsAndCerts(self, resource_id: str) -> None:
        load_skills_and_certs(self, resource_id)

    @Slot()
    def loadResourceAssignments(self) -> None:
        load_resource_assignments(self)

    @Slot(int)
    def setResourcePage(self, page: int) -> None:
        set_resource_page(self, page)

    @Slot(int)
    def setResourcePageSize(self, page_size: int) -> None:
        set_resource_page_size(self, page_size)

    # ── Bulk ─────────────────────────────────────────────────────────────

    @Slot(str, bool)
    def setResourceBulkSelection(self, resource_id: str, selected: bool) -> None:
        set_resource_bulk_selection(self, resource_id, selected)

    @Slot()
    def clearResourceBulkSelection(self) -> None:
        clear_resource_bulk_selection(self)

    @Slot()
    def selectVisibleResources(self) -> None:
        select_visible_resources(self)

    @Slot("QVariantList", result="QVariantMap")
    def bulkDeleteResources(self, resource_ids: list) -> dict[str, object]:
        return bulk_delete_resources(self, resource_ids)

    # ── Skills / Certifications ──────────────────────────────────────────

    @Slot("QVariantMap", result="QVariantMap")
    def addSkill(self, payload: dict[str, object]) -> dict[str, object]:
        return add_skill(self, payload)

    @Slot(str, result="QVariantMap")
    def removeSkill(self, skill_id: str) -> dict[str, object]:
        return remove_skill(self, skill_id)

    @Slot("QVariantMap", result="QVariantMap")
    def addCertification(self, payload: dict[str, object]) -> dict[str, object]:
        return add_certification(self, payload)

    @Slot(str, result="QVariantMap")
    def removeCertification(self, cert_id: str) -> dict[str, object]:
        return remove_certification(self, cert_id)

    # ── Export ───────────────────────────────────────────────────────────

    @Slot("QVariantList", str, result="QVariantMap")
    def exportResources(self, columns: list, file_path: str) -> dict[str, object]:
        return export_resources(self, columns, file_path)

    # ── CRUD ─────────────────────────────────────────────────────────────

    @Slot(str, "QVariantMap", result=str)
    def generateEntityCode(self, entity_type: str, payload: dict[str, object]) -> str:
        return generate_entity_code(self, entity_type, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def createResource(self, payload: dict[str, object]) -> dict[str, object]:
        return create_resource(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def updateResource(self, payload: dict[str, object]) -> dict[str, object]:
        return update_resource(self, payload)

    @Slot(str, int, result="QVariantMap")
    def toggleResourceActive(self, resource_id: str, expected_version: int) -> dict[str, object]:
        return toggle_resource_active(self, resource_id, expected_version)

    @Slot(str, result="QVariantMap")
    def deleteResource(self, resource_id: str) -> dict[str, object]:
        return delete_resource(self, resource_id)


__all__ = ["ProjectManagementResourcesWorkspaceController"]
