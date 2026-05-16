from __future__ import annotations

from PySide6.QtCore import Property, Signal, Slot

from src.ui_qml.modules.maintenance.controllers.common import (
    MaintenanceWorkspaceControllerBase,
    run_mutation,
    serialize_workspace_view_model,
)
from src.ui_qml.modules.maintenance.presenters import (
    MaintenancePreventiveWorkspacePresenter,
    MaintenanceWorkspacePresenter,
)


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
            state = self._preventive_workspace_presenter.build_workspace_state(
                queue_site_filter=self._queue_site_filter,
                queue_due_state_filter=self._queue_due_state_filter,
                queue_search_text=self._queue_search_text,
                selected_queue_plan_id=self._selected_queue_plan_id or None,
                plan_site_filter=self._plan_site_filter,
                plan_asset_filter=self._plan_asset_filter,
                plan_system_filter=self._plan_system_filter,
                plan_active_filter=self._plan_active_filter,
                plan_status_filter=self._plan_status_filter,
                plan_type_filter=self._plan_type_filter,
                plan_trigger_mode_filter=self._plan_trigger_mode_filter,
                plan_search_text=self._plan_search_text,
                selected_plan_id=self._selected_plan_id or None,
                selected_plan_task_id=self._selected_plan_task_id or None,
                template_active_filter=self._template_active_filter,
                template_maintenance_type_filter=self._template_maintenance_type_filter,
                template_status_filter=self._template_status_filter,
                template_search_text=self._template_search_text,
                selected_task_template_id=self._selected_task_template_id or None,
                selected_task_step_id=self._selected_task_step_id or None,
                generation_results=self._latest_generation_results,
            )
            self._set_overview(state["overview"])
            self._set_queue_state(state["queueState"])
            self._set_plan_library_state(state["planLibraryState"])
            self._set_template_library_state(state["templateLibraryState"])
            self._set_plan_form_options(state["planFormOptions"])
            self._set_plan_task_form_options(state["planTaskFormOptions"])
            self._set_template_form_options(state["templateFormOptions"])
            self._set_step_form_options(state["stepFormOptions"])
            self._sync_internal_state_from_maps()
            self._set_empty_state("")
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._set_error_message(str(exc))
        finally:
            self._set_is_loading(False)

    @Slot(str)
    def setQueueSiteFilter(self, site_id: str) -> None:
        normalized = (site_id or "").strip() or "all"
        if normalized == self._queue_site_filter:
            return
        self._queue_site_filter = normalized
        self._selected_queue_plan_id = ""
        self._latest_generation_results = []
        self.refresh()

    @Slot(str)
    def setQueueDueStateFilter(self, due_state: str) -> None:
        normalized = (due_state or "").strip() or "all"
        if normalized == self._queue_due_state_filter:
            return
        self._queue_due_state_filter = normalized
        self._selected_queue_plan_id = ""
        self._latest_generation_results = []
        self.refresh()

    @Slot(str)
    def setQueueSearchText(self, search_text: str) -> None:
        normalized = (search_text or "").strip()
        if normalized == self._queue_search_text:
            return
        self._queue_search_text = normalized
        self._selected_queue_plan_id = ""
        self._latest_generation_results = []
        self.refresh()

    @Slot(str)
    def selectQueuePlan(self, plan_id: str) -> None:
        normalized = (plan_id or "").strip()
        if normalized == self._selected_queue_plan_id:
            return
        self._selected_queue_plan_id = normalized
        self._latest_generation_results = []
        self.refresh()

    @Slot(str, result="QVariantMap")
    def regeneratePlanSchedule(self, plan_id: str) -> dict[str, object]:
        normalized = (plan_id or "").strip()
        if not normalized:
            return {"ok": False, "message": "Select a preventive plan first."}
        self._set_is_busy(True)
        self._set_error_message("")
        try:
            self._preventive_workspace_presenter.regenerate_plan_schedule(plan_id=normalized)
            self._latest_generation_results = []
            self.refresh()
            self._set_feedback_message("Preventive schedule regenerated.")
            return {"ok": True, "message": "Preventive schedule regenerated."}
        except Exception as exc:
            self._set_feedback_message("")
            self._set_error_message(str(exc))
            return {"ok": False, "message": str(exc)}
        finally:
            self._set_is_busy(False)

    @Slot(str, result="QVariantMap")
    def generateDueWork(self, plan_id: str) -> dict[str, object]:
        normalized = (plan_id or "").strip()
        if not normalized:
            return {"ok": False, "message": "Select a preventive plan first."}
        self._set_is_busy(True)
        self._set_error_message("")
        try:
            self._latest_generation_results = (
                self._preventive_workspace_presenter.generate_due_work(plan_id=normalized)
            )
            self.refresh()
            self._set_feedback_message("Due work generated.")
            return {"ok": True, "message": "Due work generated."}
        except Exception as exc:
            self._set_feedback_message("")
            self._set_error_message(str(exc))
            return {"ok": False, "message": str(exc)}
        finally:
            self._set_is_busy(False)

    @Slot(str)
    def setPlanSiteFilter(self, site_id: str) -> None:
        normalized = (site_id or "").strip() or "all"
        if normalized == self._plan_site_filter:
            return
        self._plan_site_filter = normalized
        self._selected_plan_id = ""
        self._selected_plan_task_id = ""
        self.refresh()

    @Slot(str)
    def setPlanAssetFilter(self, asset_id: str) -> None:
        normalized = (asset_id or "").strip() or "all"
        if normalized == self._plan_asset_filter:
            return
        self._plan_asset_filter = normalized
        self._selected_plan_id = ""
        self._selected_plan_task_id = ""
        self.refresh()

    @Slot(str)
    def setPlanSystemFilter(self, system_id: str) -> None:
        normalized = (system_id or "").strip() or "all"
        if normalized == self._plan_system_filter:
            return
        self._plan_system_filter = normalized
        self._selected_plan_id = ""
        self._selected_plan_task_id = ""
        self.refresh()

    @Slot(str)
    def setPlanActiveFilter(self, active_filter: str) -> None:
        normalized = (active_filter or "").strip() or "all"
        if normalized == self._plan_active_filter:
            return
        self._plan_active_filter = normalized
        self._selected_plan_id = ""
        self._selected_plan_task_id = ""
        self.refresh()

    @Slot(str)
    def setPlanStatusFilter(self, status: str) -> None:
        normalized = (status or "").strip() or "all"
        if normalized == self._plan_status_filter:
            return
        self._plan_status_filter = normalized
        self._selected_plan_id = ""
        self._selected_plan_task_id = ""
        self.refresh()

    @Slot(str)
    def setPlanTypeFilter(self, plan_type: str) -> None:
        normalized = (plan_type or "").strip() or "all"
        if normalized == self._plan_type_filter:
            return
        self._plan_type_filter = normalized
        self._selected_plan_id = ""
        self._selected_plan_task_id = ""
        self.refresh()

    @Slot(str)
    def setPlanTriggerModeFilter(self, trigger_mode: str) -> None:
        normalized = (trigger_mode or "").strip() or "all"
        if normalized == self._plan_trigger_mode_filter:
            return
        self._plan_trigger_mode_filter = normalized
        self._selected_plan_id = ""
        self._selected_plan_task_id = ""
        self.refresh()

    @Slot(str)
    def setPlanSearchText(self, search_text: str) -> None:
        normalized = (search_text or "").strip()
        if normalized == self._plan_search_text:
            return
        self._plan_search_text = normalized
        self._selected_plan_id = ""
        self._selected_plan_task_id = ""
        self.refresh()

    @Slot(str)
    def selectPlan(self, plan_id: str) -> None:
        normalized = (plan_id or "").strip()
        if normalized == self._selected_plan_id:
            return
        self._selected_plan_id = normalized
        self._selected_plan_task_id = ""
        self.refresh()

    @Slot(str)
    def selectPlanTask(self, plan_task_id: str) -> None:
        normalized = (plan_task_id or "").strip()
        if normalized == self._selected_plan_task_id:
            return
        self._selected_plan_task_id = normalized
        self.refresh()

    @Slot("QVariantMap", result="QVariantMap")
    def createPlan(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._preventive_workspace_presenter.create_plan(dict(payload)),
            success_message="Preventive plan created.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updatePlan(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._preventive_workspace_presenter.update_plan(dict(payload)),
            success_message="Preventive plan updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, bool, int, result="QVariantMap")
    def togglePlanActive(
        self,
        plan_id: str,
        is_active: bool,
        expected_version: int,
    ) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._preventive_workspace_presenter.toggle_plan_active(
                plan_id=plan_id,
                is_active=is_active,
                expected_version=expected_version,
            ),
            success_message="Preventive plan updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def createPlanTask(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._preventive_workspace_presenter.create_plan_task(dict(payload)),
            success_message="Plan task created.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updatePlanTask(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._preventive_workspace_presenter.update_plan_task(dict(payload)),
            success_message="Plan task updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str)
    def setTemplateActiveFilter(self, active_filter: str) -> None:
        normalized = (active_filter or "").strip() or "all"
        if normalized == self._template_active_filter:
            return
        self._template_active_filter = normalized
        self._selected_task_template_id = ""
        self._selected_task_step_id = ""
        self.refresh()

    @Slot(str)
    def setTemplateMaintenanceTypeFilter(self, maintenance_type: str) -> None:
        normalized = (maintenance_type or "").strip() or "all"
        if normalized == self._template_maintenance_type_filter:
            return
        self._template_maintenance_type_filter = normalized
        self._selected_task_template_id = ""
        self._selected_task_step_id = ""
        self.refresh()

    @Slot(str)
    def setTemplateStatusFilter(self, template_status: str) -> None:
        normalized = (template_status or "").strip() or "all"
        if normalized == self._template_status_filter:
            return
        self._template_status_filter = normalized
        self._selected_task_template_id = ""
        self._selected_task_step_id = ""
        self.refresh()

    @Slot(str)
    def setTemplateSearchText(self, search_text: str) -> None:
        normalized = (search_text or "").strip()
        if normalized == self._template_search_text:
            return
        self._template_search_text = normalized
        self._selected_task_template_id = ""
        self._selected_task_step_id = ""
        self.refresh()

    @Slot(str)
    def selectTaskTemplate(self, task_template_id: str) -> None:
        normalized = (task_template_id or "").strip()
        if normalized == self._selected_task_template_id:
            return
        self._selected_task_template_id = normalized
        self._selected_task_step_id = ""
        self.refresh()

    @Slot(str)
    def selectTaskStep(self, task_step_template_id: str) -> None:
        normalized = (task_step_template_id or "").strip()
        if normalized == self._selected_task_step_id:
            return
        self._selected_task_step_id = normalized
        self.refresh()

    @Slot("QVariantMap", result="QVariantMap")
    def createTaskTemplate(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._preventive_workspace_presenter.create_task_template(dict(payload)),
            success_message="Task template created.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateTaskTemplate(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._preventive_workspace_presenter.update_task_template(dict(payload)),
            success_message="Task template updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, bool, int, result="QVariantMap")
    def toggleTaskTemplateActive(
        self,
        task_template_id: str,
        is_active: bool,
        expected_version: int,
    ) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._preventive_workspace_presenter.toggle_task_template_active(
                task_template_id=task_template_id,
                is_active=is_active,
                expected_version=expected_version,
            ),
            success_message="Task template updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def createTaskStep(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._preventive_workspace_presenter.create_task_step(dict(payload)),
            success_message="Task step created.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateTaskStep(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._preventive_workspace_presenter.update_task_step(dict(payload)),
            success_message="Task step updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, bool, int, result="QVariantMap")
    def toggleTaskStepActive(
        self,
        task_step_template_id: str,
        is_active: bool,
        expected_version: int,
    ) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._preventive_workspace_presenter.toggle_task_step_active(
                task_step_template_id=task_step_template_id,
                is_active=is_active,
                expected_version=expected_version,
            ),
            success_message="Task step updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    def _bind_domain_events(self) -> None:
        self._subscribe_domain_change(scope_code="maintenance_management")
        self._subscribe_domain_change("site", scope_code="platform")

    def _sync_internal_state_from_maps(self) -> None:
        queue_state = self._queue_state or {}
        plan_state = self._plan_library_state or {}
        template_state = self._template_library_state or {}
        self._queue_site_filter = str(queue_state.get("selectedSiteFilter", "all") or "all")
        self._queue_due_state_filter = str(queue_state.get("selectedDueStateFilter", "all") or "all")
        self._queue_search_text = str(queue_state.get("searchText", "") or "")
        self._selected_queue_plan_id = str(queue_state.get("selectedPlanId", "") or "")
        self._plan_site_filter = str(plan_state.get("selectedSiteFilter", "all") or "all")
        self._plan_asset_filter = str(plan_state.get("selectedAssetFilter", "all") or "all")
        self._plan_system_filter = str(plan_state.get("selectedSystemFilter", "all") or "all")
        self._plan_active_filter = str(plan_state.get("selectedActiveFilter", "all") or "all")
        self._plan_status_filter = str(plan_state.get("selectedStatusFilter", "all") or "all")
        self._plan_type_filter = str(plan_state.get("selectedPlanTypeFilter", "all") or "all")
        self._plan_trigger_mode_filter = str(plan_state.get("selectedTriggerModeFilter", "all") or "all")
        self._plan_search_text = str(plan_state.get("searchText", "") or "")
        self._selected_plan_id = str(plan_state.get("selectedPlanId", "") or "")
        self._selected_plan_task_id = str(plan_state.get("selectedPlanTaskId", "") or "")
        self._template_active_filter = str(template_state.get("selectedActiveFilter", "all") or "all")
        self._template_maintenance_type_filter = str(
            template_state.get("selectedMaintenanceTypeFilter", "all") or "all"
        )
        self._template_status_filter = str(template_state.get("selectedStatusFilter", "all") or "all")
        self._template_search_text = str(template_state.get("searchText", "") or "")
        self._selected_task_template_id = str(template_state.get("selectedTaskTemplateId", "") or "")
        self._selected_task_step_id = str(template_state.get("selectedTaskStepId", "") or "")

    def _set_overview(self, overview: dict[str, object]) -> None:
        if overview == self._overview:
            return
        self._overview = overview
        self.overviewChanged.emit()

    def _set_queue_state(self, state: dict[str, object]) -> None:
        if state == self._queue_state:
            return
        self._queue_state = state
        self.queueStateChanged.emit()

    def _set_plan_library_state(self, state: dict[str, object]) -> None:
        if state == self._plan_library_state:
            return
        self._plan_library_state = state
        self.planLibraryStateChanged.emit()

    def _set_template_library_state(self, state: dict[str, object]) -> None:
        if state == self._template_library_state:
            return
        self._template_library_state = state
        self.templateLibraryStateChanged.emit()

    def _set_plan_form_options(self, options: dict[str, object]) -> None:
        if options == self._plan_form_options:
            return
        self._plan_form_options = options
        self.planFormOptionsChanged.emit()

    def _set_plan_task_form_options(self, options: dict[str, object]) -> None:
        if options == self._plan_task_form_options:
            return
        self._plan_task_form_options = options
        self.planTaskFormOptionsChanged.emit()

    def _set_template_form_options(self, options: dict[str, object]) -> None:
        if options == self._template_form_options:
            return
        self._template_form_options = options
        self.templateFormOptionsChanged.emit()

    def _set_step_form_options(self, options: dict[str, object]) -> None:
        if options == self._step_form_options:
            return
        self._step_form_options = options
        self.stepFormOptionsChanged.emit()


__all__ = ["MaintenancePreventiveWorkspaceController"]
