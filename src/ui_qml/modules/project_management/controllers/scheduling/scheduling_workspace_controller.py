from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.ui_qml.modules.project_management.controllers.common import (
    ProjectManagementWorkspaceControllerBase,
    run_mutation,
    serialize_scheduling_baselines_view_model,
    serialize_scheduling_calendar_view_model,
    serialize_scheduling_collection_view_model,
    serialize_scheduling_overview_view_model,
    serialize_selector_options,
    serialize_workspace_view_model,
)
from src.ui_qml.modules.project_management.presenters import (
    ProjectManagementWorkspacePresenter,
    ProjectSchedulingWorkspacePresenter,
)


class ProjectManagementSchedulingWorkspaceController(
    ProjectManagementWorkspaceControllerBase
):
    overviewChanged = Signal()
    projectOptionsChanged = Signal()
    selectedProjectIdChanged = Signal()
    calendarChanged = Signal()
    baselinesChanged = Signal()
    scheduleChanged = Signal()
    criticalPathChanged = Signal()
    calculatorResultChanged = Signal()

    def __init__(
        self,
        *,
        workspace_presenter: ProjectManagementWorkspacePresenter | None = None,
        scheduling_workspace_presenter: ProjectSchedulingWorkspacePresenter | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._workspace_presenter = workspace_presenter or ProjectManagementWorkspacePresenter(
            "project_management.scheduling"
        )
        self._scheduling_workspace_presenter = (
            scheduling_workspace_presenter or ProjectSchedulingWorkspacePresenter()
        )
        self._overview: dict[str, object] = {"title": "", "subtitle": "", "metrics": []}
        self._project_options: list[dict[str, str]] = []
        self._selected_project_id = ""
        self._calendar: dict[str, object] = {
            "summaryText": "",
            "workingDays": [],
            "hoursPerDay": "8",
            "holidays": [],
            "emptyState": "",
        }
        self._baselines: dict[str, object] = {
            "options": [],
            "selectedBaselineAId": "",
            "selectedBaselineBId": "",
            "includeUnchanged": False,
            "summaryText": "",
            "rows": [],
            "emptyState": "",
        }
        self._schedule: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._critical_path: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._calculator_result = ""
        self._bind_domain_events()
        self.refresh()

    @Property("QVariantMap", notify=overviewChanged)
    def overview(self) -> dict[str, object]:
        return self._overview

    @Property("QVariantList", notify=projectOptionsChanged)
    def projectOptions(self) -> list[dict[str, str]]:
        return self._project_options

    @Property(str, notify=selectedProjectIdChanged)
    def selectedProjectId(self) -> str:
        return self._selected_project_id

    @Property("QVariantMap", notify=calendarChanged)
    def calendar(self) -> dict[str, object]:
        return self._calendar

    @Property("QVariantMap", notify=baselinesChanged)
    def baselines(self) -> dict[str, object]:
        return self._baselines

    @Property("QVariantMap", notify=scheduleChanged)
    def schedule(self) -> dict[str, object]:
        return self._schedule

    @Property("QVariantMap", notify=criticalPathChanged)
    def criticalPath(self) -> dict[str, object]:
        return self._critical_path

    @Property(str, notify=calculatorResultChanged)
    def calculatorResult(self) -> str:
        return self._calculator_result

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
            workspace_state = self._scheduling_workspace_presenter.build_workspace_state(
                project_id=self._selected_project_id or None,
                selected_baseline_a_id=self._baselines.get("selectedBaselineAId") or None,
                selected_baseline_b_id=self._baselines.get("selectedBaselineBId") or None,
                include_unchanged=bool(self._baselines.get("includeUnchanged", False)),
            )
            self._set_overview(
                serialize_scheduling_overview_view_model(workspace_state.overview)
            )
            self._set_project_options(
                serialize_selector_options(workspace_state.project_options)
            )
            self._set_selected_project_id(workspace_state.selected_project_id)
            self._set_calendar(
                serialize_scheduling_calendar_view_model(workspace_state.calendar)
            )
            self._set_baselines(
                serialize_scheduling_baselines_view_model(workspace_state.baselines)
            )
            self._set_schedule(
                serialize_scheduling_collection_view_model(workspace_state.schedule)
            )
            self._set_critical_path(
                serialize_scheduling_collection_view_model(workspace_state.critical_path)
            )
            self._set_empty_state(
                workspace_state.schedule.empty_state
                or workspace_state.baselines.empty_state
            )
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._set_error_message(str(exc))
        finally:
            self._set_is_loading(False)

    @Slot(str)
    def selectProject(self, project_id: str) -> None:
        normalized_value = (project_id or "").strip()
        if normalized_value == self._selected_project_id:
            return
        self._set_selected_project_id(normalized_value)
        self._set_baselines(
            {
                **self._baselines,
                "selectedBaselineAId": "",
                "selectedBaselineBId": "",
            }
        )
        self.refresh()

    @Slot(str)
    def selectBaselineA(self, baseline_id: str) -> None:
        normalized_value = (baseline_id or "").strip()
        if normalized_value == str(self._baselines.get("selectedBaselineAId") or ""):
            return
        self._set_baselines(
            {
                **self._baselines,
                "selectedBaselineAId": normalized_value,
            }
        )
        self.refresh()

    @Slot(str)
    def selectBaselineB(self, baseline_id: str) -> None:
        normalized_value = (baseline_id or "").strip()
        if normalized_value == str(self._baselines.get("selectedBaselineBId") or ""):
            return
        self._set_baselines(
            {
                **self._baselines,
                "selectedBaselineBId": normalized_value,
            }
        )
        self.refresh()

    @Slot(bool)
    def setIncludeUnchanged(self, include_unchanged: bool) -> None:
        if bool(self._baselines.get("includeUnchanged", False)) == include_unchanged:
            return
        self._set_baselines(
            {
                **self._baselines,
                "includeUnchanged": include_unchanged,
            }
        )
        self.refresh()

    @Slot("QVariantMap", result="QVariantMap")
    def saveCalendar(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._scheduling_workspace_presenter.save_calendar(
                dict(payload)
            ),
            success_message="Working calendar updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def addHoliday(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._scheduling_workspace_presenter.add_holiday(
                dict(payload)
            ),
            success_message="Non-working day added.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def deleteHoliday(self, holiday_id: str) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._scheduling_workspace_presenter.delete_holiday(
                holiday_id
            ),
            success_message="Non-working day removed.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def createBaseline(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._scheduling_workspace_presenter.create_baseline(
                dict(payload)
            ),
            success_message="Baseline created.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def deleteBaseline(self, baseline_id: str) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._scheduling_workspace_presenter.delete_baseline(
                baseline_id
            ),
            success_message="Baseline deleted.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(result="QVariantMap")
    def recalculateSchedule(self) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._scheduling_workspace_presenter.recalculate_schedule(
                self._selected_project_id
            ),
            success_message="Schedule recalculated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def calculateWorkingDays(self, payload: dict[str, object]) -> dict[str, object]:
        self._set_error_message("")
        try:
            result = self._scheduling_workspace_presenter.calculate_working_days(
                dict(payload)
            )
        except Exception as exc:
            self._set_calculator_result("")
            self._set_feedback_message("")
            self._set_error_message(str(exc))
            return {"ok": False, "message": str(exc)}
        self._set_calculator_result(result)
        self._set_feedback_message("")
        return {"ok": True, "message": result}

    def _bind_domain_events(self) -> None:
        self._subscribe_domain_change(
            "project",
            "project_tasks",
            "project_baseline",
            scope_code="project_management",
        )

    def _set_overview(self, overview: dict[str, object]) -> None:
        if overview == self._overview:
            return
        self._overview = overview
        self.overviewChanged.emit()

    def _set_project_options(self, project_options: list[dict[str, str]]) -> None:
        if project_options == self._project_options:
            return
        self._project_options = project_options
        self.projectOptionsChanged.emit()

    def _set_selected_project_id(self, selected_project_id: str) -> None:
        if selected_project_id == self._selected_project_id:
            return
        self._selected_project_id = selected_project_id
        self.selectedProjectIdChanged.emit()

    def _set_calendar(self, calendar: dict[str, object]) -> None:
        if calendar == self._calendar:
            return
        self._calendar = calendar
        self.calendarChanged.emit()

    def _set_baselines(self, baselines: dict[str, object]) -> None:
        if baselines == self._baselines:
            return
        self._baselines = baselines
        self.baselinesChanged.emit()

    def _set_schedule(self, schedule: dict[str, object]) -> None:
        if schedule == self._schedule:
            return
        self._schedule = schedule
        self.scheduleChanged.emit()

    def _set_critical_path(self, critical_path: dict[str, object]) -> None:
        if critical_path == self._critical_path:
            return
        self._critical_path = critical_path
        self.criticalPathChanged.emit()

    def _set_calculator_result(self, calculator_result: str) -> None:
        if calculator_result == self._calculator_result:
            return
        self._calculator_result = calculator_result
        self.calculatorResultChanged.emit()


__all__ = ["ProjectManagementSchedulingWorkspaceController"]
