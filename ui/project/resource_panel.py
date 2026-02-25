from __future__ import annotations

from typing import Optional

from PySide6 import QtCore
from PySide6.QtWidgets import (
    QDialog,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.exceptions import BusinessRuleError, NotFoundError
from core.models import Project
from core.services.project import ProjectResourceService
from core.services.resource import ResourceService
from ui.project.dialogs import ProjectResourceEditDialog
from ui.shared.guards import apply_permission_hint, make_guarded_slot
from ui.styles.style_utils import style_table
from ui.styles.ui_config import UIConfig as CFG


class ProjectResourcePanelMixin:
    _project_resource_service: ProjectResourceService
    _resource_service: ResourceService

    _project_resource_table: QTableWidget
    _project_resource_title: QLabel
    _project_resource_summary: QLabel
    _btn_project_resource_add: QPushButton
    _btn_project_resource_edit: QPushButton
    _btn_project_resource_toggle: QPushButton

    def _build_project_resource_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("projectResourcesPanel")
        panel.setStyleSheet(
            f"""
            QWidget#projectResourcesPanel {{
                background-color: {CFG.COLOR_BG_SURFACE};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 10px;
            }}
            """
        )
        layout = QVBoxLayout(panel)
        layout.setSpacing(CFG.SPACING_SM)
        layout.setContentsMargins(CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM)

        title = QLabel("Project Resources")
        title.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        layout.addWidget(title)

        self._project_resource_title = QLabel("Select a project to manage resources.")
        self._project_resource_title.setStyleSheet(CFG.INFO_TEXT_STYLE)
        self._project_resource_title.setWordWrap(True)
        layout.addWidget(self._project_resource_title)

        self._project_resource_summary = QLabel("")
        self._project_resource_summary.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        self._project_resource_summary.setWordWrap(True)
        layout.addWidget(self._project_resource_summary)

        self._project_resource_table = QTableWidget(0, 6)
        self._project_resource_table.setHorizontalHeaderLabels(
            ["Resource", "Default Rate", "Project Rate", "Currency", "Planned Hours", "Active"]
        )
        self._project_resource_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._project_resource_table.setSelectionMode(QTableWidget.SingleSelection)
        self._project_resource_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._project_resource_table.setMinimumHeight(240)
        style_table(self._project_resource_table)
        hdr = self._project_resource_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.Stretch)
        layout.addWidget(self._project_resource_table, 1)

        btn_row = QHBoxLayout()
        self._btn_project_resource_add = QPushButton(CFG.ADD_BUTTON_LABEL)
        self._btn_project_resource_edit = QPushButton(CFG.EDIT_LABEL)
        self._btn_project_resource_toggle = QPushButton("Toggle Active")
        for btn in (
            self._btn_project_resource_add,
            self._btn_project_resource_edit,
            self._btn_project_resource_toggle,
        ):
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)
        btn_row.addWidget(self._btn_project_resource_add)
        btn_row.addWidget(self._btn_project_resource_edit)
        btn_row.addWidget(self._btn_project_resource_toggle)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._btn_project_resource_add.clicked.connect(
            make_guarded_slot(
                self,
                title="Project Resources",
                callback=self._on_add_project_resource_inline,
            )
        )
        self._btn_project_resource_edit.clicked.connect(
            make_guarded_slot(
                self,
                title="Project Resources",
                callback=self._on_edit_project_resource_inline,
            )
        )
        self._btn_project_resource_toggle.clicked.connect(
            make_guarded_slot(
                self,
                title="Project Resources",
                callback=self._on_toggle_project_resource_inline,
            )
        )
        self._project_resource_table.itemSelectionChanged.connect(
            self._sync_project_resource_panel_actions
        )
        can_manage = bool(getattr(self, "_can_manage_project_resources", True))
        apply_permission_hint(
            self._btn_project_resource_add,
            allowed=can_manage,
            missing_permission="project.manage",
        )
        apply_permission_hint(
            self._btn_project_resource_edit,
            allowed=can_manage,
            missing_permission="project.manage",
        )
        apply_permission_hint(
            self._btn_project_resource_toggle,
            allowed=can_manage,
            missing_permission="project.manage",
        )
        self._sync_project_resource_panel_actions()
        return panel

    def _on_project_selection_changed(self, *_args) -> None:
        self._reload_project_resource_panel_for_selected_project()

    def _reload_project_resource_panel_for_selected_project(self) -> None:
        project = self._get_selected_project()
        self._project_resource_table.setRowCount(0)
        if not project:
            self._project_resource_title.setText("Select a project to manage resources.")
            self._project_resource_summary.setText("")
            self._sync_project_resource_panel_actions()
            return

        self._project_resource_title.setText(f"Project: {project.name}")
        rows = self._project_resource_service.list_by_project(project.id)

        self._project_resource_table.setRowCount(len(rows))
        active_count = 0
        for row, pr in enumerate(rows):
            try:
                res = self._resource_service.get_resource(pr.resource_id)
            except NotFoundError:
                res = None

            name = res.name if res else f"<missing resource> ({pr.resource_id})"
            default_rate = getattr(res, "hourly_rate", None) if res else None
            default_cur = getattr(res, "currency_code", "") if res else ""
            project_rate = "" if pr.hourly_rate is None else f"{float(pr.hourly_rate):,.2f}"
            cur = (pr.currency_code or default_cur or "").upper()
            planned_hours = f"{float(pr.planned_hours or 0.0):,.2f}"
            is_active = bool(getattr(pr, "is_active", True))
            if is_active:
                active_count += 1

            name_item = QTableWidgetItem(name)
            name_item.setData(QtCore.Qt.UserRole, pr.id)
            values = [
                name_item,
                QTableWidgetItem("" if default_rate is None else f"{float(default_rate):,.2f}"),
                QTableWidgetItem(project_rate),
                QTableWidgetItem(cur),
                QTableWidgetItem(planned_hours),
                QTableWidgetItem("Yes" if is_active else "No"),
            ]
            for col, item in enumerate(values):
                if col in (1, 2, 4):
                    item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                self._project_resource_table.setItem(row, col, item)

        self._project_resource_summary.setText(
            f"{len(rows)} resources linked | Active: {active_count} | Inactive: {len(rows) - active_count}"
        )
        self._project_resource_table.clearSelection()
        self._sync_project_resource_panel_actions()

    def _selected_project_resource_id_inline(self) -> Optional[str]:
        row = self._project_resource_table.currentRow()
        if row < 0:
            return None
        item = self._project_resource_table.item(row, 0)
        return item.data(QtCore.Qt.UserRole) if item else None

    def _on_add_project_resource_inline(self) -> None:
        project = self._get_selected_project()
        if not project:
            QMessageBox.information(self, "Project Resources", "Please select a project.")
            return
        dlg = ProjectResourceEditDialog(
            project_id=project.id,
            resource_service=self._resource_service,
            project_resource_service=self._project_resource_service,
            project_resource_id=None,
            parent=self,
        )
        if dlg.exec() == QDialog.Accepted:
            self._reload_project_resource_panel_for_selected_project()

    def _on_edit_project_resource_inline(self) -> None:
        project = self._get_selected_project()
        if not project:
            QMessageBox.information(self, "Project Resources", "Please select a project.")
            return
        pr_id = self._selected_project_resource_id_inline()
        if not pr_id:
            QMessageBox.information(self, "Edit", "Please select a row to edit.")
            return
        dlg = ProjectResourceEditDialog(
            project_id=project.id,
            resource_service=self._resource_service,
            project_resource_service=self._project_resource_service,
            project_resource_id=pr_id,
            parent=self,
        )
        if dlg.exec() == QDialog.Accepted:
            self._reload_project_resource_panel_for_selected_project()

    def _on_toggle_project_resource_inline(self) -> None:
        pr_id = self._selected_project_resource_id_inline()
        if not pr_id:
            QMessageBox.information(self, "Status", "Please select a row.")
            return
        pr = self._project_resource_service.get(pr_id)
        if not pr:
            QMessageBox.warning(self, "Status", "Selected item no longer exists.")
            self._reload_project_resource_panel_for_selected_project()
            return
        try:
            self._project_resource_service.set_active(
                pr_id,
                not bool(getattr(pr, "is_active", True)),
            )
        except (BusinessRuleError, NotFoundError) as exc:
            QMessageBox.warning(self, "Status", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Status", str(exc))
            return
        self._reload_project_resource_panel_for_selected_project()

    def _sync_project_resource_panel_actions(self) -> None:
        has_project = self._get_selected_project() is not None
        has_row = self._selected_project_resource_id_inline() is not None
        can_manage = bool(getattr(self, "_can_manage_project_resources", True))
        self._btn_project_resource_add.setEnabled(can_manage and has_project)
        self._btn_project_resource_edit.setEnabled(can_manage and has_project and has_row)
        self._btn_project_resource_toggle.setEnabled(can_manage and has_project and has_row)

    def _get_selected_project(self) -> Optional[Project]:
        raise NotImplementedError
