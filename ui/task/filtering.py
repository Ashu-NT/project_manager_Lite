from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

from core.domain.enums import TaskStatus
from core.models import Task
from ui.styles.ui_config import UIConfig as CFG


class TaskFiltersMixin:
    def _build_task_filters(self, layout: QVBoxLayout) -> None:
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Search:"))
        self.task_search_filter = QLineEdit()
        self.task_search_filter.setPlaceholderText("Task name or description...")
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

        self.btn_clear_task_filters = QPushButton("Clear Filters")
        self.btn_clear_task_filters.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.btn_clear_task_filters.setFixedHeight(CFG.BUTTON_HEIGHT)
        bar.addWidget(self.btn_clear_task_filters)
        layout.addLayout(bar)

        self.task_search_filter.textChanged.connect(self._on_task_filters_changed)
        self.task_status_filter.currentIndexChanged.connect(self._on_task_filters_changed)
        self.btn_clear_task_filters.clicked.connect(self._clear_task_filters)

    def _on_task_filters_changed(self, *_args) -> None:
        self._refresh_tasks_from_cache()

    def _clear_task_filters(self) -> None:
        self.task_search_filter.blockSignals(True)
        self.task_status_filter.blockSignals(True)
        self.task_search_filter.clear()
        self.task_status_filter.setCurrentIndex(0)
        self.task_search_filter.blockSignals(False)
        self.task_status_filter.blockSignals(False)
        self._refresh_tasks_from_cache()

    def _apply_task_filters(self, tasks: list[Task]) -> list[Task]:
        query = self.task_search_filter.text().strip().lower()
        status = str(self.task_status_filter.currentData() or "").strip()
        filtered: list[Task] = []
        for task in tasks:
            if status and getattr(task.status, "value", str(task.status)) != status:
                continue
            if query:
                haystack = " ".join([task.name or "", task.description or ""]).lower()
                if query not in haystack:
                    continue
            filtered.append(task)
        return filtered


__all__ = ["TaskFiltersMixin"]
