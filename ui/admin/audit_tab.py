from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.events.domain_events import domain_events
from core.exceptions import BusinessRuleError
from core.models import AuditLogEntry
from core.services.audit import AuditService
from core.services.baseline import BaselineService
from core.services.cost import CostService
from core.services.project import ProjectService
from core.services.resource import ResourceService
from core.services.task import TaskService
from ui.styles.style_utils import style_table
from ui.styles.ui_config import UIConfig as CFG


class AuditLogTab(QWidget):
    def __init__(
        self,
        audit_service: AuditService,
        project_service: ProjectService,
        task_service: TaskService | None = None,
        resource_service: ResourceService | None = None,
        cost_service: CostService | None = None,
        baseline_service: BaselineService | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._audit_service = audit_service
        self._project_service = project_service
        self._task_service = task_service
        self._resource_service = resource_service
        self._cost_service = cost_service
        self._baseline_service = baseline_service
        self._rows: list[AuditLogEntry] = []
        self._project_name_by_id: dict[str, str] = {}
        self._task_name_by_id: dict[str, str] = {}
        self._resource_name_by_id: dict[str, str] = {}
        self._cost_label_by_id: dict[str, str] = {}
        self._baseline_name_by_id: dict[str, str] = {}
        self._setup_ui()
        self.reload_logs()
        self._connect_domain_events()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        title = QLabel("Audit Log")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        subtitle = QLabel("Immutable activity trail for governance and core create/update/delete operations.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Project:"))
        self.project_filter = QComboBox()
        self.project_filter.setFixedHeight(CFG.INPUT_HEIGHT)
        toolbar.addWidget(self.project_filter)
        toolbar.addWidget(QLabel("Entity:"))
        self.entity_filter = QComboBox()
        self.entity_filter.setFixedHeight(CFG.INPUT_HEIGHT)
        self.entity_filter.addItem("All", userData="")
        self.entity_filter.addItem("Approval", userData="approval_request")
        self.entity_filter.addItem("Project", userData="project")
        self.entity_filter.addItem("Task", userData="task")
        self.entity_filter.addItem("Dependency", userData="task_dependency")
        self.entity_filter.addItem("Resource", userData="resource")
        self.entity_filter.addItem("Cost", userData="cost_item")
        self.entity_filter.addItem("Baseline", userData="project_baseline")
        toolbar.addWidget(self.entity_filter)
        toolbar.addWidget(QLabel("Action:"))
        self.action_filter = QLineEdit()
        self.action_filter.setPlaceholderText("Contains...")
        self.action_filter.setMinimumHeight(CFG.INPUT_HEIGHT)
        toolbar.addWidget(self.action_filter)
        toolbar.addWidget(QLabel("Actor:"))
        self.actor_filter = QLineEdit()
        self.actor_filter.setPlaceholderText("Username...")
        self.actor_filter.setMinimumHeight(CFG.INPUT_HEIGHT)
        toolbar.addWidget(self.actor_filter)
        self.btn_refresh = QPushButton(CFG.REFRESH_BUTTON_LABEL)
        self.btn_refresh.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_refresh.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        toolbar.addWidget(self.btn_refresh)
        layout.addLayout(toolbar)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Occurred At", "Actor", "Action", "Entity", "Project", "Details"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        style_table(self.table)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        layout.addWidget(self.table, 1)

        self.project_filter.currentIndexChanged.connect(self._apply_filters)
        self.entity_filter.currentIndexChanged.connect(self._apply_filters)
        self.action_filter.textChanged.connect(self._apply_filters)
        self.actor_filter.textChanged.connect(self._apply_filters)
        self.btn_refresh.clicked.connect(self.reload_logs)

    def _connect_domain_events(self) -> None:
        domain_events.project_changed.connect(self._on_domain_event)
        domain_events.tasks_changed.connect(self._on_domain_event)
        domain_events.costs_changed.connect(self._on_domain_event)
        domain_events.resources_changed.connect(self._on_domain_event)
        domain_events.baseline_changed.connect(self._on_domain_event)
        domain_events.approvals_changed.connect(self._on_domain_event)

    def _on_domain_event(self, _payload: str) -> None:
        self.reload_logs()

    def reload_logs(self) -> None:
        try:
            self._rows = self._audit_service.list_recent(limit=1000)
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Audit Log", str(exc))
            self._rows = []
        except Exception as exc:
            QMessageBox.critical(self, "Audit Log", f"Failed to load audit records:\n{exc}")
            self._rows = []
        self._refresh_reference_maps()
        self._reload_project_filter()
        self._apply_filters()

    def _refresh_reference_maps(self) -> None:
        self._project_name_by_id.clear()
        self._task_name_by_id.clear()
        self._resource_name_by_id.clear()
        self._cost_label_by_id.clear()
        self._baseline_name_by_id.clear()

        try:
            projects = self._project_service.list_projects()
        except BusinessRuleError:
            projects = []
        for project in projects:
            self._project_name_by_id[project.id] = project.name

        if self._task_service is not None:
            for project in projects:
                try:
                    tasks = self._task_service.list_tasks_for_project(project.id)
                except BusinessRuleError:
                    tasks = []
                for task in tasks:
                    self._task_name_by_id[task.id] = task.name

        if self._resource_service is not None:
            try:
                resources = self._resource_service.list_resources()
            except BusinessRuleError:
                resources = []
            for resource in resources:
                self._resource_name_by_id[resource.id] = resource.name

        if self._cost_service is not None:
            for project in projects:
                try:
                    items = self._cost_service.list_cost_items_for_project(project.id)
                except BusinessRuleError:
                    items = []
                for item in items:
                    self._cost_label_by_id[item.id] = item.description

        if self._baseline_service is not None:
            for project in projects:
                try:
                    baselines = self._baseline_service.list_baselines(project.id)
                except BusinessRuleError:
                    baselines = []
                for baseline in baselines:
                    self._baseline_name_by_id[baseline.id] = baseline.name

    def _reload_project_filter(self) -> None:
        selected = self.project_filter.currentData()
        self.project_filter.blockSignals(True)
        self.project_filter.clear()
        self.project_filter.addItem("All", userData="")
        for project_id, project_name in sorted(self._project_name_by_id.items(), key=lambda item: item[1].lower()):
            self.project_filter.addItem(project_name, userData=project_id)
        idx = self.project_filter.findData(selected) if selected else 0
        self.project_filter.setCurrentIndex(idx if idx >= 0 else 0)
        self.project_filter.blockSignals(False)

    def _apply_filters(self) -> None:
        project_id = str(self.project_filter.currentData() or "").strip()
        entity_type = str(self.entity_filter.currentData() or "").strip()
        action_query = self.action_filter.text().strip().lower()
        actor_query = self.actor_filter.text().strip().lower()

        filtered = [
            row
            for row in self._rows
            if (not project_id or (row.project_id or "") == project_id)
            and (not entity_type or row.entity_type == entity_type)
            and (not action_query or action_query in row.action.lower())
            and (not actor_query or actor_query in (row.actor_username or "").lower())
        ]
        self._populate_table(filtered)

    def _populate_table(self, rows: list[AuditLogEntry]) -> None:
        self.table.setRowCount(len(rows))
        for row_idx, entry in enumerate(rows):
            entity_label = self._entity_label(entry)
            project_label = self._project_name_by_id.get(entry.project_id or "", entry.project_id or "-")
            details_label = self._details_label(entry)
            values = (
                entry.occurred_at.strftime("%Y-%m-%d %H:%M:%S"),
                entry.actor_username or "system",
                entry.action,
                entity_label,
                project_label or (entry.project_id or "-"),
                details_label,
            )
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col in {0, 1, 2, 3, 4}:
                    item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                self.table.setItem(row_idx, col, item)
            self.table.item(row_idx, 0).setData(Qt.UserRole, entry.id)

    def _details_label(self, entry: AuditLogEntry) -> str:
        details = entry.details or {}
        if not details:
            return "-"
        pairs = []
        for key in sorted(details):
            if key.endswith("_id") and f"{key[:-3]}_name" in details:
                continue
            value = self._resolve_detail_value(entry, key, details[key])
            if value in {"", None}:
                continue
            label_key = key.replace("_name", "").replace("_id", "").replace("_", " ")
            pairs.append(f"{label_key}={value}")
        if not pairs:
            return "-"
        text = ", ".join(pairs)
        return text if len(text) <= 200 else f"{text[:197]}..."

    def _resolve_detail_value(self, entry: AuditLogEntry, key: str, value: Any) -> str:
        raw = str(value).strip() if value is not None else ""
        if key.endswith("_name"):
            return raw
        if key.endswith("_id"):
            if not raw:
                return ""
            if key in {"task_id", "predecessor_id", "successor_id"}:
                return self._task_name_by_id.get(raw, raw)
            if key == "project_id":
                return self._project_name_by_id.get(raw, raw)
            if key == "resource_id":
                return self._resource_name_by_id.get(raw, raw)
            if key == "cost_id":
                return self._cost_label_by_id.get(raw, raw)
            if key == "baseline_id":
                return self._baseline_name_by_id.get(raw, raw)
            if key == "entity_id":
                if entry.entity_type == "task":
                    return self._task_name_by_id.get(raw, raw)
                if entry.entity_type == "project":
                    return self._project_name_by_id.get(raw, raw)
                if entry.entity_type == "resource":
                    return self._resource_name_by_id.get(raw, raw)
                if entry.entity_type == "cost_item":
                    return self._cost_label_by_id.get(raw, raw)
                if entry.entity_type == "project_baseline":
                    return self._baseline_name_by_id.get(raw, raw)
            return raw
        return raw

    @staticmethod
    def _entity_label(entry: AuditLogEntry) -> str:
        entity = entry.entity_type.replace("_", " ").title()
        request_type = str((entry.details or {}).get("request_type") or "").strip()
        if request_type:
            return f"{entity} ({request_type})"
        return entity


__all__ = ["AuditLogTab"]
