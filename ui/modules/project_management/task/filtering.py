from __future__ import annotations

import re
import shlex
from datetime import date, timedelta

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from src.core.modules.project_management.domain.enums import TaskStatus
from src.core.modules.project_management.domain.tasks.task import Task
from ui.modules.project_management.dashboard.styles import dashboard_action_button_style
from src.ui.platform.settings.main_window_store import MainWindowSettingsStore
from src.ui.shared.formatting.ui_config import UIConfig as CFG


class TaskFiltersMixin:
    _settings_store: MainWindowSettingsStore | None
    _saved_task_views: dict[str, dict[str, object]]

    def _build_task_filters(self, layout: QVBoxLayout) -> None:
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Search:"))
        self.task_search_filter = QLineEdit()
        self.task_search_filter.setPlaceholderText(
            "Task name/desc | advanced: status:done priority>=70 progress<100"
        )
        self.task_search_filter.setClearButtonEnabled(True)
        self.task_search_filter.setSizePolicy(CFG.INPUT_POLICY)
        self.task_search_filter.setMinimumHeight(CFG.INPUT_HEIGHT)
        bar.addWidget(self.task_search_filter)

        bar.addWidget(QLabel("Status:"))
        self.task_status_filter = QComboBox()
        self.task_status_filter.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.task_status_filter.setFixedHeight(CFG.INPUT_HEIGHT)
        self.task_status_filter.addItem("All", userData="")
        for status in TaskStatus:
            self.task_status_filter.addItem(status.value.replace("_", " ").title(), userData=status.value)
        bar.addWidget(self.task_status_filter)

        bar.addWidget(QLabel("Priority:"))
        self.task_priority_filter = QComboBox()
        self.task_priority_filter.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.task_priority_filter.setFixedHeight(CFG.INPUT_HEIGHT)
        self.task_priority_filter.addItem("All", userData="all")
        self.task_priority_filter.addItem("High (>= 70)", userData="high")
        self.task_priority_filter.addItem("Medium (30-69)", userData="medium")
        self.task_priority_filter.addItem("Low (< 30)", userData="low")
        bar.addWidget(self.task_priority_filter)

        bar.addWidget(QLabel("Schedule:"))
        self.task_schedule_filter = QComboBox()
        self.task_schedule_filter.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.task_schedule_filter.setFixedHeight(CFG.INPUT_HEIGHT)
        self.task_schedule_filter.addItem("All", userData="all")
        self.task_schedule_filter.addItem("Overdue", userData="overdue")
        self.task_schedule_filter.addItem("Due 7 days", userData="due_7")
        self.task_schedule_filter.addItem("No deadline", userData="no_deadline")
        bar.addWidget(self.task_schedule_filter)

        self.btn_clear_task_filters = QPushButton("Clear Filters")
        self.btn_clear_task_filters.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.btn_clear_task_filters.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_clear_task_filters.setStyleSheet(dashboard_action_button_style("secondary"))
        bar.addWidget(self.btn_clear_task_filters)
        layout.addLayout(bar)

        saved_bar = QHBoxLayout()
        saved_bar.addWidget(QLabel("Saved View:"))
        self.task_view_combo = QComboBox()
        self.task_view_combo.setSizePolicy(CFG.INPUT_POLICY)
        self.task_view_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        saved_bar.addWidget(self.task_view_combo)
        self.btn_apply_task_view = QPushButton("Apply View")
        self.btn_save_task_view = QPushButton("Save View")
        self.btn_delete_task_view = QPushButton("Delete View")
        for btn, variant in (
            (self.btn_apply_task_view, "secondary"),
            (self.btn_save_task_view, "primary"),
            (self.btn_delete_task_view, "danger"),
        ):
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)
            btn.setStyleSheet(dashboard_action_button_style(variant))
            saved_bar.addWidget(btn)
        saved_bar.addStretch()
        layout.addLayout(saved_bar)

        self._saved_task_views = {}
        self._load_task_saved_views()
        self._refresh_task_view_combo()

        self.task_search_filter.textChanged.connect(self._on_task_filters_changed)
        self.task_status_filter.currentIndexChanged.connect(self._on_task_filters_changed)
        self.task_priority_filter.currentIndexChanged.connect(self._on_task_filters_changed)
        self.task_schedule_filter.currentIndexChanged.connect(self._on_task_filters_changed)
        self.btn_clear_task_filters.clicked.connect(self._clear_task_filters)
        self.btn_save_task_view.clicked.connect(self._save_current_task_view)
        self.btn_apply_task_view.clicked.connect(self._apply_selected_task_view)
        self.btn_delete_task_view.clicked.connect(self._delete_selected_task_view)

    def _on_task_filters_changed(self, *_args) -> None:
        self._refresh_tasks_from_cache()

    def _clear_task_filters(self) -> None:
        self.task_search_filter.blockSignals(True)
        self.task_status_filter.blockSignals(True)
        self.task_priority_filter.blockSignals(True)
        self.task_schedule_filter.blockSignals(True)
        self.task_search_filter.clear()
        self.task_status_filter.setCurrentIndex(0)
        self.task_priority_filter.setCurrentIndex(0)
        self.task_schedule_filter.setCurrentIndex(0)
        self.task_search_filter.blockSignals(False)
        self.task_status_filter.blockSignals(False)
        self.task_priority_filter.blockSignals(False)
        self.task_schedule_filter.blockSignals(False)
        self._refresh_tasks_from_cache()

    def _apply_task_filters(self, tasks: list[Task]) -> list[Task]:
        query = self.task_search_filter.text().strip()
        status = str(self.task_status_filter.currentData() or "").strip()
        priority_mode = str(self.task_priority_filter.currentData() or "all").strip()
        schedule_mode = str(self.task_schedule_filter.currentData() or "all").strip()
        free_terms, structured = self._parse_advanced_task_query(query)
        today = date.today()
        due_cutoff = today + timedelta(days=7)

        filtered: list[Task] = []
        for task in tasks:
            if status and getattr(task.status, "value", str(task.status)) != status:
                continue
            if priority_mode == "high" and int(task.priority or 0) < 70:
                continue
            if priority_mode == "medium" and not (30 <= int(task.priority or 0) <= 69):
                continue
            if priority_mode == "low" and int(task.priority or 0) >= 30:
                continue
            deadline = getattr(task, "deadline", None)
            if schedule_mode == "overdue" and not (deadline and deadline < today):
                continue
            if schedule_mode == "due_7" and not (deadline and today <= deadline <= due_cutoff):
                continue
            if schedule_mode == "no_deadline" and deadline is not None:
                continue
            if not self._task_matches_advanced_query(task, free_terms, structured):
                continue
            filtered.append(task)
        return filtered

    def _load_task_saved_views(self) -> None:
        store = getattr(self, "_settings_store", None)
        if store is None:
            self._saved_task_views = {}
            return
        self._saved_task_views = store.load_task_saved_views()

    def _persist_task_saved_views(self) -> None:
        store = getattr(self, "_settings_store", None)
        if store is None:
            return
        store.save_task_saved_views(self._saved_task_views)

    def _refresh_task_view_combo(self) -> None:
        combo = getattr(self, "task_view_combo", None)
        if combo is None:
            return
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("Current Filters", userData="")
        for name in sorted(self._saved_task_views):
            combo.addItem(name, userData=name)
        combo.blockSignals(False)
        combo.setCurrentIndex(0)

    def _capture_task_filter_state(self) -> dict[str, object]:
        return {
            "query": self.task_search_filter.text().strip(),
            "status": int(self.task_status_filter.currentIndex()),
            "priority": int(self.task_priority_filter.currentIndex()),
            "schedule": int(self.task_schedule_filter.currentIndex()),
        }

    def _apply_task_filter_state(self, state: dict[str, object]) -> None:
        self.task_search_filter.blockSignals(True)
        self.task_status_filter.blockSignals(True)
        self.task_priority_filter.blockSignals(True)
        self.task_schedule_filter.blockSignals(True)
        self.task_search_filter.setText(str(state.get("query", "") or ""))
        self.task_status_filter.setCurrentIndex(max(0, int(state.get("status", 0))))
        self.task_priority_filter.setCurrentIndex(max(0, int(state.get("priority", 0))))
        self.task_schedule_filter.setCurrentIndex(max(0, int(state.get("schedule", 0))))
        self.task_search_filter.blockSignals(False)
        self.task_status_filter.blockSignals(False)
        self.task_priority_filter.blockSignals(False)
        self.task_schedule_filter.blockSignals(False)
        self._refresh_tasks_from_cache()

    def _save_current_task_view(self) -> None:
        name, ok = QInputDialog.getText(self, "Save Task View", "View name:")
        view_name = (name or "").strip()
        if not ok or not view_name:
            return
        self._saved_task_views[view_name] = self._capture_task_filter_state()
        self._persist_task_saved_views()
        self._refresh_task_view_combo()
        idx = self.task_view_combo.findData(view_name)
        if idx >= 0:
            self.task_view_combo.setCurrentIndex(idx)

    def _apply_selected_task_view(self) -> None:
        view_name = str(self.task_view_combo.currentData() or "").strip()
        if not view_name:
            self._refresh_tasks_from_cache()
            return
        state = self._saved_task_views.get(view_name)
        if isinstance(state, dict):
            self._apply_task_filter_state(state)

    def _delete_selected_task_view(self) -> None:
        view_name = str(self.task_view_combo.currentData() or "").strip()
        if not view_name:
            return
        self._saved_task_views.pop(view_name, None)
        self._persist_task_saved_views()
        self._refresh_task_view_combo()

    @staticmethod
    def _parse_advanced_task_query(query: str) -> tuple[list[str], list[tuple[str, str, str]]]:
        terms: list[str] = []
        structured: list[tuple[str, str, str]] = []
        for token in shlex.split(query or ""):
            match = re.match(
                r"^(status|priority|progress|start|end|deadline)(:|<=|>=|=|<|>)(.+)$",
                token,
                flags=re.IGNORECASE,
            )
            if not match:
                terms.append(token.lower())
                continue
            field, op, value = match.groups()
            structured.append((field.lower(), op, value.strip()))
        return terms, structured

    def _task_matches_advanced_query(
        self,
        task: Task,
        terms: list[str],
        structured: list[tuple[str, str, str]],
    ) -> bool:
        haystack = " ".join([task.name or "", task.description or ""]).lower()
        for term in terms:
            if term and term not in haystack:
                return False

        for field, op, value in structured:
            if field == "status":
                actual = getattr(task.status, "value", str(task.status)).lower()
                if op in {":", "="} and actual != value.lower():
                    return False
                if op in {"!=", "<>"} and actual == value.lower():
                    return False
                continue

            if field in {"priority", "progress"}:
                number = int(task.priority or 0) if field == "priority" else float(task.percent_complete or 0.0)
                try:
                    threshold = float(value)
                except ValueError:
                    return False
                if not self._compare_numeric(number, op, threshold):
                    return False
                continue

            if field in {"start", "end", "deadline"}:
                actual_date = getattr(task, f"{field}_date", None) if field in {"start", "end"} else getattr(task, "deadline", None)
                try:
                    expected_date = date.fromisoformat(value)
                except ValueError:
                    return False
                if actual_date is None:
                    return False
                if not self._compare_date(actual_date, op, expected_date):
                    return False

        return True

    @staticmethod
    def _compare_numeric(actual: float, op: str, expected: float) -> bool:
        if op == ":":
            op = "="
        if op == "=":
            return abs(actual - expected) < 1e-9
        if op == ">=":
            return actual >= expected
        if op == "<=":
            return actual <= expected
        if op == ">":
            return actual > expected
        if op == "<":
            return actual < expected
        return False

    @staticmethod
    def _compare_date(actual: date, op: str, expected: date) -> bool:
        if op == ":":
            op = "="
        if op == "=":
            return actual == expected
        if op == ">=":
            return actual >= expected
        if op == "<=":
            return actual <= expected
        if op == ">":
            return actual > expected
        if op == "<":
            return actual < expected
        return False


__all__ = ["TaskFiltersMixin"]
