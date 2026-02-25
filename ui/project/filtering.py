from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

from core.domain.enums import ProjectStatus
from core.models import Project
from ui.styles.ui_config import UIConfig as CFG


class ProjectFiltersMixin:
    _all_projects: list[Project]

    def _build_project_filters(self, layout: QVBoxLayout) -> None:
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Search:"))
        self.project_search_filter = QLineEdit()
        self.project_search_filter.setPlaceholderText("Name, client, description...")
        self.project_search_filter.setClearButtonEnabled(True)
        self.project_search_filter.setSizePolicy(CFG.INPUT_POLICY)
        self.project_search_filter.setMinimumHeight(CFG.INPUT_HEIGHT)
        bar.addWidget(self.project_search_filter)

        bar.addWidget(QLabel("Status:"))
        self.project_status_filter = QComboBox()
        self.project_status_filter.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.project_status_filter.setFixedHeight(CFG.INPUT_HEIGHT)
        self.project_status_filter.addItem("All", userData="")
        for status in ProjectStatus:
            self.project_status_filter.addItem(status.value.replace("_", " ").title(), userData=status.value)
        bar.addWidget(self.project_status_filter)

        self.btn_clear_project_filters = QPushButton("Clear Filters")
        self.btn_clear_project_filters.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.btn_clear_project_filters.setFixedHeight(CFG.BUTTON_HEIGHT)
        bar.addWidget(self.btn_clear_project_filters)
        layout.addLayout(bar)

        self.project_search_filter.textChanged.connect(self._on_project_filters_changed)
        self.project_status_filter.currentIndexChanged.connect(self._on_project_filters_changed)
        self.btn_clear_project_filters.clicked.connect(self._clear_project_filters)

    def _on_project_filters_changed(self, *_args) -> None:
        selected = self._get_selected_project()
        selected_id = selected.id if selected else None
        self._render_project_rows(preferred_project_id=selected_id)

    def _clear_project_filters(self) -> None:
        self.project_search_filter.blockSignals(True)
        self.project_status_filter.blockSignals(True)
        self.project_search_filter.clear()
        self.project_status_filter.setCurrentIndex(0)
        self.project_search_filter.blockSignals(False)
        self.project_status_filter.blockSignals(False)
        self._render_project_rows(preferred_project_id=None)

    def _apply_project_filters(self, projects: list[Project]) -> list[Project]:
        query = self.project_search_filter.text().strip().lower()
        status = str(self.project_status_filter.currentData() or "").strip()
        filtered: list[Project] = []
        for project in projects:
            if status and getattr(project.status, "value", str(project.status)) != status:
                continue
            if query:
                haystack = " ".join(
                    [
                        project.name or "",
                        project.client_name or "",
                        project.description or "",
                        project.currency or "",
                    ]
                ).lower()
                if query not in haystack:
                    continue
            filtered.append(project)
        return filtered

    def _render_project_rows(self, preferred_project_id: Optional[str]) -> None:
        visible_projects = self._apply_project_filters(list(self._all_projects))
        self.model.set_projects(visible_projects)
        if not visible_projects:
            self._reload_project_resource_panel_for_selected_project()
            self._sync_actions()
            return

        row = 0
        if preferred_project_id:
            for idx, project in enumerate(visible_projects):
                if project.id == preferred_project_id:
                    row = idx
                    break
        self.table.selectRow(row)
        self._reload_project_resource_panel_for_selected_project()
        self._sync_actions()


__all__ = ["ProjectFiltersMixin"]
