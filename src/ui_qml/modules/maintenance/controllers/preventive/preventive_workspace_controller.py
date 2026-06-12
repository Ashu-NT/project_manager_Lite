from __future__ import annotations

from PySide6.QtCore import Property, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.modules.maintenance.controllers.common import (
    MaintenanceWorkspaceControllerBase,
)
from src.ui_qml.modules.maintenance.presenters import (
    MaintenancePreventiveWorkspacePresenter,
    MaintenanceWorkspacePresenter,
)
from .preventive_generation_actions import (
    generate_due_work,
    regenerate_plan_schedule,
)
from .preventive_plan_actions import (
    apply_plan_active_filter,
    apply_plan_asset_filter,
    apply_plan_search_text,
    apply_plan_site_filter,
    apply_plan_status_filter,
    apply_plan_system_filter,
    apply_plan_trigger_mode_filter,
    apply_plan_type_filter,
    apply_select_plan,
    apply_select_plan_task,
    create_plan,
    create_plan_task,
    toggle_plan_active,
    update_plan,
    update_plan_task,
)
from .preventive_queue_actions import (
    apply_queue_due_state_filter,
    apply_queue_search_text,
    apply_queue_site_filter,
    apply_select_queue_plan,
)
from .preventive_state_loader import load_workspace_state
from .preventive_template_actions import (
    apply_select_task_step,
    apply_select_task_template,
    apply_template_active_filter,
    apply_template_maintenance_type_filter,
    apply_template_search_text,
    apply_template_status_filter,
    create_task_step,
    create_task_template,
    toggle_task_step_active,
    toggle_task_template_active,
    update_task_step,
    update_task_template,
)

QML_IMPORT_NAME = "Maintenance.Controllers"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
@QmlUncreatable("Maintenance workspace controllers are provided by the shell runtime.")
class MaintenancePreventiveWorkspaceController(MaintenanceWorkspaceControllerBase):
    overviewChanged = Signal()
    queueStateChanged = Signal()
    planLibraryStateChanged = Signal()
    templateLibraryStateChanged = Signal()
    planFormOptionsChanged = Signal()
    planTaskFormOptionsChanged = Signal()
    templateFormOptionsChanged = Signal()
    stepFormOptionsChanged = Signal()

    def __init__(
        self,
        *,
        workspace_presenter: MaintenanceWorkspacePresenter | None = None,
        preventive_workspace_presenter: MaintenancePreventiveWorkspacePresenter | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._workspace_presenter = workspace_presenter or MaintenanceWorkspacePresenter(
            "maintenance_management.preventive"
        )
        self._preventive_workspace_presenter = (
            preventive_workspace_presenter or MaintenancePreventiveWorkspacePresenter()
        )
        self._overview: dict[str, object] = {"title": "", "subtitle": "", "metrics": []}
        self._queue_state: dict[str, object] = {}
        self._plan_library_state: dict[str, object] = {}
        self._template_library_state: dict[str, object] = {}
        self._plan_form_options: dict[str, object] = {}
        self._plan_task_form_options: dict[str, object] = {}
        self._template_form_options: dict[str, object] = {}
        self._step_form_options: dict[str, object] = {}
        self._queue_site_filter = "all"
        self._queue_due_state_filter = "all"
        self._queue_search_text = ""
        self._selected_queue_plan_id = ""
        self._plan_site_filter = "all"
        self._plan_asset_filter = "all"
        self._plan_system_filter = "all"
        self._plan_active_filter = "all"
        self._plan_status_filter = "all"
        self._plan_type_filter = "all"
        self._plan_trigger_mode_filter = "all"
        self._plan_search_text = ""
        self._selected_plan_id = ""
        self._selected_plan_task_id = ""
        self._template_active_filter = "all"
        self._template_maintenance_type_filter = "all"
        self._template_status_filter = "all"
        self._template_search_text = ""
        self._selected_task_template_id = ""
        self._selected_task_step_id = ""
        self._latest_generation_results: list[dict[str, object]] = []
        self._bind_domain_events()
        self.refresh()

    # --- Qt Properties ---

    @Property("QVariantMap", notify=overviewChanged)
    def overview(self) -> dict[str, object]:
        return self._overview

    @Property("QVariantMap", notify=queueStateChanged)
    def queueState(self) -> dict[str, object]:
        return self._queue_state

    @Property("QVariantMap", notify=planLibraryStateChanged)
    def planLibraryState(self) -> dict[str, object]:
        return self._plan_library_state

    @Property("QVariantMap", notify=templateLibraryStateChanged)
    def templateLibraryState(self) -> dict[str, object]:
        return self._template_library_state

    @Property("QVariantMap", notify=planFormOptionsChanged)
    def planFormOptions(self) -> dict[str, object]:
        return self._plan_form_options

    @Property("QVariantMap", notify=planTaskFormOptionsChanged)
    def planTaskFormOptions(self) -> dict[str, object]:
        return self._plan_task_form_options

    @Property("QVariantMap", notify=templateFormOptionsChanged)
    def templateFormOptions(self) -> dict[str, object]:
        return self._template_form_options

    @Property("QVariantMap", notify=stepFormOptionsChanged)
    def stepFormOptions(self) -> dict[str, object]:
        return self._step_form_options

    # --- Slots ---

    @Slot()
    def refresh(self) -> None:
        load_workspace_state(self)

    @Slot(str)
    def setQueueSiteFilter(self, site_id: str) -> None:
        apply_queue_site_filter(self, site_id)

    @Slot(str)
    def setQueueDueStateFilter(self, due_state: str) -> None:
        apply_queue_due_state_filter(self, due_state)

    @Slot(str)
    def setQueueSearchText(self, search_text: str) -> None:
        apply_queue_search_text(self, search_text)

    @Slot(str)
    def selectQueuePlan(self, plan_id: str) -> None:
        apply_select_queue_plan(self, plan_id)

    @Slot(str, result="QVariantMap")
    def regeneratePlanSchedule(self, plan_id: str) -> dict[str, object]:
        return regenerate_plan_schedule(self, plan_id)

    @Slot(str, result="QVariantMap")
    def generateDueWork(self, plan_id: str) -> dict[str, object]:
        return generate_due_work(self, plan_id)

    @Slot(str)
    def setPlanSiteFilter(self, site_id: str) -> None:
        apply_plan_site_filter(self, site_id)

    @Slot(str)
    def setPlanAssetFilter(self, asset_id: str) -> None:
        apply_plan_asset_filter(self, asset_id)

    @Slot(str)
    def setPlanSystemFilter(self, system_id: str) -> None:
        apply_plan_system_filter(self, system_id)

    @Slot(str)
    def setPlanActiveFilter(self, active_filter: str) -> None:
        apply_plan_active_filter(self, active_filter)

    @Slot(str)
    def setPlanStatusFilter(self, status: str) -> None:
        apply_plan_status_filter(self, status)

    @Slot(str)
    def setPlanTypeFilter(self, plan_type: str) -> None:
        apply_plan_type_filter(self, plan_type)

    @Slot(str)
    def setPlanTriggerModeFilter(self, trigger_mode: str) -> None:
        apply_plan_trigger_mode_filter(self, trigger_mode)

    @Slot(str)
    def setPlanSearchText(self, search_text: str) -> None:
        apply_plan_search_text(self, search_text)

    @Slot(str)
    def selectPlan(self, plan_id: str) -> None:
        apply_select_plan(self, plan_id)

    @Slot(str)
    def selectPlanTask(self, plan_task_id: str) -> None:
        apply_select_plan_task(self, plan_task_id)

    @Slot("QVariantMap", result="QVariantMap")
    def createPlan(self, payload: dict[str, object]) -> dict[str, object]:
        return create_plan(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def updatePlan(self, payload: dict[str, object]) -> dict[str, object]:
        return update_plan(self, payload)

    @Slot(str, bool, int, result="QVariantMap")
    def togglePlanActive(
        self, plan_id: str, is_active: bool, expected_version: int
    ) -> dict[str, object]:
        return toggle_plan_active(self, plan_id, is_active, expected_version)

    @Slot("QVariantMap", result="QVariantMap")
    def createPlanTask(self, payload: dict[str, object]) -> dict[str, object]:
        return create_plan_task(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def updatePlanTask(self, payload: dict[str, object]) -> dict[str, object]:
        return update_plan_task(self, payload)

    @Slot(str)
    def setTemplateActiveFilter(self, active_filter: str) -> None:
        apply_template_active_filter(self, active_filter)

    @Slot(str)
    def setTemplateMaintenanceTypeFilter(self, maintenance_type: str) -> None:
        apply_template_maintenance_type_filter(self, maintenance_type)

    @Slot(str)
    def setTemplateStatusFilter(self, template_status: str) -> None:
        apply_template_status_filter(self, template_status)

    @Slot(str)
    def setTemplateSearchText(self, search_text: str) -> None:
        apply_template_search_text(self, search_text)

    @Slot(str)
    def selectTaskTemplate(self, task_template_id: str) -> None:
        apply_select_task_template(self, task_template_id)

    @Slot(str)
    def selectTaskStep(self, task_step_template_id: str) -> None:
        apply_select_task_step(self, task_step_template_id)

    @Slot("QVariantMap", result="QVariantMap")
    def createTaskTemplate(self, payload: dict[str, object]) -> dict[str, object]:
        return create_task_template(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def updateTaskTemplate(self, payload: dict[str, object]) -> dict[str, object]:
        return update_task_template(self, payload)

    @Slot(str, bool, int, result="QVariantMap")
    def toggleTaskTemplateActive(
        self, task_template_id: str, is_active: bool, expected_version: int
    ) -> dict[str, object]:
        return toggle_task_template_active(
            self, task_template_id, is_active, expected_version
        )

    @Slot("QVariantMap", result="QVariantMap")
    def createTaskStep(self, payload: dict[str, object]) -> dict[str, object]:
        return create_task_step(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def updateTaskStep(self, payload: dict[str, object]) -> dict[str, object]:
        return update_task_step(self, payload)

    @Slot(str, bool, int, result="QVariantMap")
    def toggleTaskStepActive(
        self, task_step_template_id: str, is_active: bool, expected_version: int
    ) -> dict[str, object]:
        return toggle_task_step_active(
            self, task_step_template_id, is_active, expected_version
        )

    # --- Domain event wiring ---

    def _bind_domain_events(self) -> None:
        self._subscribe_domain_change(scope_code="maintenance_management")
        self._subscribe_domain_change("site", scope_code="platform")


__all__ = ["MaintenancePreventiveWorkspaceController"]
