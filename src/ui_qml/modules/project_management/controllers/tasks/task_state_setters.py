from __future__ import annotations


class TaskStateSettersMixin:
    """Mixin that provides all coordinator-state setter methods for the tasks workspace facade."""

    def _set_task_page(self, v: int) -> None:
        if v == self._task_page:
            return
        self._task_page = v
        self.taskPageChanged.emit()

    def _set_task_page_size(self, v: int) -> None:
        if v == self._task_page_size:
            return
        self._task_page_size = v
        self.taskPageSizeChanged.emit()

    def _set_task_total_count(self, v: int) -> None:
        if v == self._task_total_count:
            return
        self._task_total_count = v
        self.taskTotalCountChanged.emit()

    def _set_selected_project_id(self, v: str) -> None:
        if v == self._selected_project_id:
            return
        self._selected_project_id = v
        self.selectedProjectIdChanged.emit()

    def _set_selected_status_filter(self, v: str) -> None:
        if v == self._selected_status_filter:
            return
        self._selected_status_filter = v
        self.selectedStatusFilterChanged.emit()

    def _set_selected_priority_filter(self, v: str) -> None:
        if v == self._selected_priority_filter:
            return
        self._selected_priority_filter = v
        self.selectedPriorityFilterChanged.emit()

    def _set_selected_schedule_filter(self, v: str) -> None:
        if v == self._selected_schedule_filter:
            return
        self._selected_schedule_filter = v
        self.selectedScheduleFilterChanged.emit()

    def _set_search_text(self, v: str) -> None:
        if v == self._search_text:
            return
        self._search_text = v
        self.searchTextChanged.emit()

    def _set_selected_task_view_name(self, v: str) -> None:
        if v == self._selected_task_view_name:
            return
        self._selected_task_view_name = v
        self.selectedTaskViewNameChanged.emit()

    def _set_selected_task_id(self, v: str) -> None:
        if v == self._selected_task_id:
            return
        self._selected_task_id = v
        self.selectedTaskIdChanged.emit()
        if self._task_review_active:
            self._collab_ctrl.sync_review_presence(v)

    def _set_selected_assignment_id(self, v: str) -> None:
        if v == self._selected_assignment_id:
            return
        self._selected_assignment_id = v
        self.selectedAssignmentIdChanged.emit()

    def _set_selected_time_period_start(self, v: str) -> None:
        if v == self._selected_time_period_start:
            return
        self._selected_time_period_start = v
        self.selectedTimePeriodStartChanged.emit()

    def _set_selected_time_entry_id(self, v: str) -> None:
        if v == self._selected_time_entry_id:
            return
        self._selected_time_entry_id = v
        self.selectedTimeEntryIdChanged.emit()

    def _set_time_section_loaded_for_task_id(self, task_id: str) -> None:
        normalized = (task_id or "").strip()
        if normalized == self._time_section_loaded_for_task_id:
            return
        self._time_section_loaded_for_task_id = normalized
        self.timeSectionLoadedChanged.emit()

    def _set_collaboration_section_loaded_for_task_id(self, task_id: str) -> None:
        normalized = (task_id or "").strip()
        if normalized == self._collaboration_section_loaded_for_task_id:
            return
        self._collaboration_section_loaded_for_task_id = normalized
        self.collaborationSectionLoadedChanged.emit()

    def _set_schedule_impact(self, v: dict[str, object]) -> None:
        if v == self._schedule_impact:
            return
        self._schedule_impact = v
        self.scheduleImpactChanged.emit()
        self.scheduleImpactSectionLoadedChanged.emit()


__all__ = ["TaskStateSettersMixin"]
