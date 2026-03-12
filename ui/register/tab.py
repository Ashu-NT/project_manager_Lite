from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QGroupBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.domain.register import RegisterEntry, RegisterEntrySeverity, RegisterEntryStatus, RegisterEntryType
from core.domain.register import as_register_entry_severity, as_register_entry_status, as_register_entry_type
from core.events.domain_events import domain_events
from core.exceptions import BusinessRuleError, ValidationError
from core.services.auth import UserSessionContext
from core.services.project import ProjectService
from core.services.register import RegisterService
from ui.register.dialogs import RegisterEntryDialog
from ui.shared.guards import apply_permission_hint, has_permission, make_guarded_slot
from ui.styles.style_utils import style_table
from ui.styles.ui_config import UIConfig as CFG


class RegisterTab(QWidget):
    def __init__(
        self,
        *,
        register_service: RegisterService,
        project_service: ProjectService,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._register_service = register_service
        self._project_service = project_service
        self._user_session = user_session
        self._can_manage = has_permission(self._user_session, "project.manage")
        self._rows: list[RegisterEntry] = []
        self._project_name_by_id: dict[str, str] = {}
        self._setup_ui()
        self.reload_entries()
        domain_events.project_changed.connect(self._on_project_catalog_changed)
        domain_events.register_changed.connect(self._on_register_changed)

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(CFG.SPACING_MD)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        title = QLabel("Risk / Issue / Change Register")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        subtitle = QLabel(
            "Track delivery risks, execution issues, and project changes with owners, due dates, and action context."
        )
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(subtitle)

        toolbar = QHBoxLayout()
        self.btn_new = QPushButton("New Entry")
        self.btn_edit = QPushButton(CFG.EDIT_LABEL)
        self.btn_delete = QPushButton(CFG.DELETE_LABEL)
        self.btn_refresh = QPushButton(CFG.REFRESH_BUTTON_LABEL)
        for btn in (self.btn_new, self.btn_edit, self.btn_delete, self.btn_refresh):
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        toolbar.addWidget(self.btn_new)
        toolbar.addWidget(self.btn_edit)
        toolbar.addWidget(self.btn_delete)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_refresh)
        root.addLayout(toolbar)

        filters = QGridLayout()
        filters.setHorizontalSpacing(CFG.SPACING_MD)
        filters.setVerticalSpacing(CFG.SPACING_SM)
        self.project_filter = QComboBox()
        self.type_filter = QComboBox()
        self.status_filter = QComboBox()
        self.severity_filter = QComboBox()
        self.owner_filter = QLineEdit()
        self.owner_filter.setPlaceholderText("Owner contains...")
        for widget in (
            self.project_filter,
            self.type_filter,
            self.status_filter,
            self.severity_filter,
            self.owner_filter,
        ):
            widget.setMinimumHeight(CFG.INPUT_HEIGHT)
        self.type_filter.addItem("All types", userData=None)
        self.status_filter.addItem("All statuses", userData=None)
        self.severity_filter.addItem("All severities", userData=None)
        for entry_type in RegisterEntryType:
            self.type_filter.addItem(entry_type.value.title(), userData=entry_type)
        for status in RegisterEntryStatus:
            self.status_filter.addItem(status.value.replace("_", " ").title(), userData=status)
        for severity in RegisterEntrySeverity:
            self.severity_filter.addItem(severity.value.title(), userData=severity)
        filters.addWidget(QLabel("Project"), 0, 0)
        filters.addWidget(self.project_filter, 0, 1)
        filters.addWidget(QLabel("Type"), 0, 2)
        filters.addWidget(self.type_filter, 0, 3)
        filters.addWidget(QLabel("Status"), 1, 0)
        filters.addWidget(self.status_filter, 1, 1)
        filters.addWidget(QLabel("Severity"), 1, 2)
        filters.addWidget(self.severity_filter, 1, 3)
        filters.addWidget(QLabel("Owner"), 2, 0)
        filters.addWidget(self.owner_filter, 2, 1, 1, 3)
        root.addLayout(filters)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(8)
        root.addWidget(splitter, 1)

        table_panel = QWidget()
        table_layout = QVBoxLayout(table_panel)
        table_layout.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Type", "Title", "Severity", "Status", "Owner", "Due"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        style_table(self.table)
        table_layout.addWidget(self.table)
        splitter.addWidget(table_panel)

        narrative_panel = QWidget()
        narrative_panel.setMinimumWidth(420)
        narrative_layout = QVBoxLayout(narrative_panel)
        narrative_layout.setContentsMargins(0, 0, 0, 0)
        narrative_layout.setSpacing(CFG.SPACING_SM)
        narrative_title = QLabel("Entry Narrative")
        narrative_title.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        narrative_layout.addWidget(narrative_title)
        self.description_view = self._build_narrative_section(
            narrative_layout,
            title="Description",
            placeholder="No description",
        )
        self.impact_view = self._build_narrative_section(
            narrative_layout,
            title="Impact",
            placeholder="No impact summary",
        )
        self.response_view = self._build_narrative_section(
            narrative_layout,
            title="Response Plan",
            placeholder="No response plan",
        )
        narrative_layout.addStretch(1)
        splitter.addWidget(narrative_panel)
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([900, 420])

        self.btn_new.clicked.connect(make_guarded_slot(self, title="Register", callback=self.create_entry))
        self.btn_edit.clicked.connect(make_guarded_slot(self, title="Register", callback=self.edit_entry))
        self.btn_delete.clicked.connect(make_guarded_slot(self, title="Register", callback=self.delete_entry))
        self.btn_refresh.clicked.connect(self.reload_entries)
        self.project_filter.currentIndexChanged.connect(self._apply_filters)
        self.type_filter.currentIndexChanged.connect(self._apply_filters)
        self.status_filter.currentIndexChanged.connect(self._apply_filters)
        self.severity_filter.currentIndexChanged.connect(self._apply_filters)
        self.owner_filter.textChanged.connect(self._apply_filters)
        self.table.itemSelectionChanged.connect(self._render_selected_entry)

        apply_permission_hint(self.btn_new, allowed=self._can_manage, missing_permission="project.manage")
        apply_permission_hint(self.btn_edit, allowed=self._can_manage, missing_permission="project.manage")
        apply_permission_hint(self.btn_delete, allowed=self._can_manage, missing_permission="project.manage")

    def _build_narrative_section(self, layout: QVBoxLayout, *, title: str, placeholder: str) -> QTextEdit:
        group = QGroupBox(title)
        section_layout = QVBoxLayout(group)
        section_layout.setContentsMargins(CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM)
        section_layout.setSpacing(CFG.SPACING_XS)
        view = QTextEdit()
        view.setReadOnly(True)
        view.setPlaceholderText(placeholder)
        view.setMinimumHeight(135)
        section_layout.addWidget(view)
        layout.addWidget(group)
        return view

    def reload_entries(self) -> None:
        try:
            self._rows = self._register_service.list_entries()
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Register", str(exc))
            self._rows = []
        except Exception as exc:
            QMessageBox.critical(self, "Register", f"Failed to load register entries:\n{exc}")
            self._rows = []
        self._reload_project_filter()
        self._apply_filters()

    def _reload_project_filter(self) -> None:
        selected = self.project_filter.currentData()
        self._project_name_by_id = {
            project.id: project.name for project in self._project_service.list_projects()
        }
        self.project_filter.blockSignals(True)
        self.project_filter.clear()
        self.project_filter.addItem("All projects", userData="")
        for project_id, name in sorted(self._project_name_by_id.items(), key=lambda item: item[1].lower()):
            self.project_filter.addItem(name, userData=project_id)
        idx = self.project_filter.findData(selected) if selected else 0
        self.project_filter.setCurrentIndex(idx if idx >= 0 else 0)
        self.project_filter.blockSignals(False)

    def _apply_filters(self) -> None:
        project_id = str(self.project_filter.currentData() or "").strip()
        entry_type = self.type_filter.currentData()
        status = self.status_filter.currentData()
        severity = self.severity_filter.currentData()
        owner_query = self.owner_filter.text().strip().lower()
        filtered = [
            row
            for row in self._rows
            if (not project_id or row.project_id == project_id)
            and (entry_type is None or row.entry_type == entry_type)
            and (status is None or row.status == status)
            and (severity is None or row.severity == severity)
            and (not owner_query or owner_query in (row.owner_name or "").lower())
        ]
        self.table.setRowCount(len(filtered))
        for row_idx, entry in enumerate(filtered):
            values = [
                as_register_entry_type(entry.entry_type).value.title(),
                entry.title,
                as_register_entry_severity(entry.severity).value.title(),
                as_register_entry_status(entry.status).value.replace("_", " ").title(),
                entry.owner_name or "-",
                entry.due_date.isoformat() if entry.due_date else "-",
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 1:
                    item.setData(Qt.UserRole, entry.id)
                self.table.setItem(row_idx, col, item)
        if filtered:
            self.table.selectRow(0)
        else:
            self._render_entry(None)
        self._sync_actions()

    def _selected_entry(self) -> RegisterEntry | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 1)
        entry_id = item.data(Qt.UserRole) if item is not None else None
        return next((entry for entry in self._rows if entry.id == entry_id), None)

    def _render_selected_entry(self) -> None:
        self._render_entry(self._selected_entry())
        self._sync_actions()

    def _render_entry(self, entry: RegisterEntry | None) -> None:
        if entry is None:
            self.description_view.clear()
            self.impact_view.clear()
            self.response_view.clear()
            return
        self.description_view.setPlainText(entry.description or "")
        self.impact_view.setPlainText(entry.impact_summary or "")
        self.response_view.setPlainText(entry.response_plan or "")

    def _sync_actions(self) -> None:
        selected = self._selected_entry() is not None
        self.btn_new.setEnabled(self._can_manage)
        self.btn_edit.setEnabled(self._can_manage and selected)
        self.btn_delete.setEnabled(self._can_manage and selected)

    def create_entry(self) -> None:
        project_id = str(self.project_filter.currentData() or "").strip()
        if not project_id:
            QMessageBox.information(self, "Register", "Select a project before creating a register entry.")
            return
        dialog = RegisterEntryDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            self._register_service.create_entry(
                project_id,
                entry_type=dialog.entry_type,
                title=dialog.title,
                description=dialog.description,
                severity=dialog.severity,
                status=dialog.status,
                owner_name=dialog.owner_name,
                due_date=dialog.due_date,
                impact_summary=dialog.impact_summary,
                response_plan=dialog.response_plan,
            )
        except (ValidationError, BusinessRuleError) as exc:
            QMessageBox.warning(self, "Register", str(exc))
            return
        self.reload_entries()

    def edit_entry(self) -> None:
        entry = self._selected_entry()
        if entry is None:
            QMessageBox.information(self, "Register", "Please select an entry.")
            return
        dialog = RegisterEntryDialog(self, entry=entry)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            self._register_service.update_entry(
                entry.id,
                expected_version=entry.version,
                entry_type=dialog.entry_type,
                title=dialog.title,
                description=dialog.description,
                severity=dialog.severity,
                status=dialog.status,
                owner_name=dialog.owner_name,
                due_date=dialog.due_date,
                impact_summary=dialog.impact_summary,
                response_plan=dialog.response_plan,
            )
        except (ValidationError, BusinessRuleError) as exc:
            QMessageBox.warning(self, "Register", str(exc))
            return
        self.reload_entries()

    def delete_entry(self) -> None:
        entry = self._selected_entry()
        if entry is None:
            QMessageBox.information(self, "Register", "Please select an entry.")
            return
        if QMessageBox.question(self, "Register", f"Delete '{entry.title}'?") != QMessageBox.Yes:
            return
        try:
            self._register_service.delete_entry(entry.id)
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Register", str(exc))
            return
        self.reload_entries()

    def _on_project_catalog_changed(self, _project_id: str) -> None:
        self.reload_entries()

    def _on_register_changed(self, _project_id: str) -> None:
        self.reload_entries()


__all__ = ["RegisterTab"]
