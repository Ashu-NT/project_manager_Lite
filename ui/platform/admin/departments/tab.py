from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.platform.auth import UserSessionContext
from core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from core.platform.common.models import Department
from core.platform.notifications.domain_events import domain_events
from core.platform.org import DepartmentService, SiteService
from ui.modules.project_management.dashboard.styles import (
    dashboard_action_button_style,
    dashboard_badge_style,
    dashboard_meta_chip_style,
)
from ui.platform.admin.departments.dialogs import DepartmentEditDialog
from ui.platform.shared.guards import apply_permission_hint, has_permission, make_guarded_slot
from ui.platform.shared.styles.style_utils import style_table
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class DepartmentAdminTab(QWidget):
    def __init__(
        self,
        department_service: DepartmentService,
        site_service: SiteService | None = None,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._department_service = department_service
        self._site_service = site_service
        self._user_session = user_session
        self._can_manage_departments = has_permission(self._user_session, "settings.manage")
        self._rows: list[Department] = []
        self._site_lookup: dict[str, str] = {}
        self._setup_ui()
        self.reload_departments()
        domain_events.departments_changed.connect(self._on_departments_changed)
        domain_events.sites_changed.connect(self._on_sites_changed)
        domain_events.organizations_changed.connect(self._on_organizations_changed)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        header = QWidget()
        header.setObjectName("departmentAdminHeaderCard")
        header.setStyleSheet(
            f"""
            QWidget#departmentAdminHeaderCard {{
                background-color: {CFG.COLOR_BG_SURFACE};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 12px;
            }}
            """
        )
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_SM, CFG.MARGIN_MD, CFG.MARGIN_SM)
        header_layout.setSpacing(CFG.SPACING_MD)
        intro = QVBoxLayout()
        intro.setSpacing(CFG.SPACING_XS)
        eyebrow = QLabel("DEPARTMENT MASTER")
        eyebrow.setStyleSheet(CFG.DASHBOARD_KPI_TITLE_STYLE)
        intro.addWidget(eyebrow)
        title = QLabel("Departments")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        intro.addWidget(title)
        subtitle = QLabel(
            "Manage shared department records for workforce context, reporting consistency, and future HR alignment."
        )
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        intro.addWidget(subtitle)
        header_layout.addLayout(intro, 1)
        status_layout = QVBoxLayout()
        status_layout.setSpacing(CFG.SPACING_SM)
        self.department_context_badge = QLabel("Context: -")
        self.department_context_badge.setStyleSheet(dashboard_badge_style(CFG.COLOR_ACCENT))
        self.department_count_badge = QLabel("0 departments")
        self.department_count_badge.setStyleSheet(dashboard_meta_chip_style())
        self.department_active_badge = QLabel("0 active")
        self.department_active_badge.setStyleSheet(dashboard_meta_chip_style())
        access_label = "Manage Enabled" if self._can_manage_departments else "Read Only"
        self.department_access_badge = QLabel(access_label)
        self.department_access_badge.setStyleSheet(dashboard_meta_chip_style())
        status_layout.addWidget(self.department_context_badge, 0, Qt.AlignRight)
        status_layout.addWidget(self.department_count_badge, 0, Qt.AlignRight)
        status_layout.addWidget(self.department_active_badge, 0, Qt.AlignRight)
        status_layout.addWidget(self.department_access_badge, 0, Qt.AlignRight)
        status_layout.addStretch(1)
        header_layout.addLayout(status_layout)
        layout.addWidget(header)

        controls = QWidget()
        controls.setObjectName("departmentAdminControlSurface")
        controls.setStyleSheet(
            f"""
            QWidget#departmentAdminControlSurface {{
                background-color: {CFG.COLOR_BG_SURFACE_ALT};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 12px;
            }}
            """
        )
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM)
        controls_layout.setSpacing(CFG.SPACING_SM)

        toolbar = QHBoxLayout()
        self.btn_refresh = QPushButton(CFG.REFRESH_BUTTON_LABEL)
        self.btn_new_department = QPushButton("New Department")
        self.btn_edit_department = QPushButton("Edit Department")
        self.btn_toggle_active = QPushButton("Toggle Active")
        for btn in (self.btn_refresh, self.btn_new_department, self.btn_edit_department, self.btn_toggle_active):
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.btn_new_department.setStyleSheet(dashboard_action_button_style("primary"))
        self.btn_edit_department.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_toggle_active.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_refresh.setStyleSheet(dashboard_action_button_style("secondary"))
        toolbar.addWidget(self.btn_new_department)
        toolbar.addWidget(self.btn_edit_department)
        toolbar.addWidget(self.btn_toggle_active)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_refresh)
        controls_layout.addLayout(toolbar)
        layout.addWidget(controls)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Code", "Name", "Site", "Type", "Active"])
        style_table(self.table)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        header_widget = self.table.horizontalHeader()
        header_widget.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header_widget.setSectionResizeMode(1, QHeaderView.Stretch)
        header_widget.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header_widget.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header_widget.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        layout.addWidget(self.table, 1)

        self.btn_refresh.clicked.connect(
            make_guarded_slot(self, title="Departments", callback=self.reload_departments)
        )
        self.btn_new_department.clicked.connect(
            make_guarded_slot(self, title="Departments", callback=self.create_department)
        )
        self.btn_edit_department.clicked.connect(
            make_guarded_slot(self, title="Departments", callback=self.edit_department)
        )
        self.btn_toggle_active.clicked.connect(
            make_guarded_slot(self, title="Departments", callback=self.toggle_active)
        )
        self.table.itemSelectionChanged.connect(self._sync_actions)
        for button in (self.btn_new_department, self.btn_edit_department, self.btn_toggle_active):
            apply_permission_hint(button, allowed=self._can_manage_departments, missing_permission="settings.manage")
        self._sync_actions()

    def reload_departments(self) -> None:
        try:
            context = self._department_service.get_context_organization()
            self._rows = self._department_service.list_departments()
            self._site_lookup = self._load_site_lookup()
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Departments", str(exc))
            context_label = "-"
            self._rows = []
            self._site_lookup = {}
        except Exception as exc:
            QMessageBox.critical(self, "Departments", f"Failed to load departments: {exc}")
            context_label = "-"
            self._rows = []
            self._site_lookup = {}
        else:
            context_label = context.display_name
        self.table.setRowCount(len(self._rows))
        for row, department in enumerate(self._rows):
            values = (
                department.department_code,
                department.name,
                self._site_lookup.get(department.site_id or "", "-"),
                department.department_type or "-",
                "Yes" if department.is_active else "No",
            )
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 4:
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)
            self.table.item(row, 0).setData(Qt.UserRole, department.id)
        self.table.clearSelection()
        self._update_header_badges(self._rows, context_label=context_label)
        self._sync_actions()

    def create_department(self) -> None:
        dlg = DepartmentEditDialog(
            parent=self,
            sites=self._available_sites(),
            parent_departments=self._rows,
        )
        while True:
            if dlg.exec() != QDialog.Accepted:
                return
            try:
                self._department_service.create_department(
                    department_code=dlg.department_code,
                    name=dlg.name,
                    description=dlg.description,
                    site_id=dlg.site_id,
                    parent_department_id=dlg.parent_department_id,
                    department_type=dlg.department_type,
                    cost_center_code=dlg.cost_center_code,
                    notes=dlg.notes,
                    is_active=dlg.is_active,
                )
            except ValidationError as exc:
                QMessageBox.warning(self, "Departments", str(exc))
                continue
            except Exception as exc:
                QMessageBox.critical(self, "Departments", f"Failed to create department: {exc}")
                return
            break
        self.reload_departments()

    def edit_department(self) -> None:
        department = self._selected_department()
        if department is None:
            QMessageBox.information(self, "Departments", "Please select a department.")
            return
        dlg = DepartmentEditDialog(
            parent=self,
            department=department,
            sites=self._available_sites(),
            parent_departments=self._rows,
        )
        while True:
            if dlg.exec() != QDialog.Accepted:
                return
            try:
                self._department_service.update_department(
                    department.id,
                    department_code=dlg.department_code,
                    name=dlg.name,
                    description=dlg.description,
                    site_id=dlg.site_id,
                    parent_department_id=dlg.parent_department_id,
                    department_type=dlg.department_type,
                    cost_center_code=dlg.cost_center_code,
                    notes=dlg.notes,
                    is_active=dlg.is_active,
                    expected_version=department.version,
                )
            except (ValidationError, NotFoundError, BusinessRuleError, ConcurrencyError) as exc:
                QMessageBox.warning(self, "Departments", str(exc))
                if isinstance(exc, ConcurrencyError):
                    self.reload_departments()
                    return
                continue
            except Exception as exc:
                QMessageBox.critical(self, "Departments", f"Failed to update department: {exc}")
                return
            break
        self.reload_departments()

    def toggle_active(self) -> None:
        department = self._selected_department()
        if department is None:
            QMessageBox.information(self, "Departments", "Please select a department.")
            return
        try:
            self._department_service.update_department(
                department.id,
                is_active=not department.is_active,
                expected_version=department.version,
            )
        except (ValidationError, NotFoundError, BusinessRuleError, ConcurrencyError) as exc:
            QMessageBox.warning(self, "Departments", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Departments", f"Failed to update department: {exc}")
            return
        self.reload_departments()

    def _selected_department(self) -> Department | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        department_id = item.data(Qt.UserRole)
        for department in self._rows:
            if department.id == department_id:
                return department
        return None

    def _update_header_badges(self, rows: list[Department], *, context_label: str) -> None:
        active_count = sum(1 for row in rows if row.is_active)
        self.department_context_badge.setText(f"Context: {context_label}")
        self.department_count_badge.setText(f"{len(rows)} departments")
        self.department_active_badge.setText(f"{active_count} active")

    def _available_sites(self):
        if self._site_service is None:
            return []
        try:
            return self._site_service.list_sites(active_only=True)
        except BusinessRuleError:
            return []

    def _load_site_lookup(self) -> dict[str, str]:
        return {site.id: site.site_code for site in self._available_sites()}

    def _on_departments_changed(self, _department_id: str) -> None:
        self.reload_departments()

    def _on_sites_changed(self, _site_id: str) -> None:
        self.reload_departments()

    def _on_organizations_changed(self, _organization_id: str) -> None:
        self.reload_departments()

    def _sync_actions(self) -> None:
        has_department = self._selected_department() is not None
        self.btn_new_department.setEnabled(self._can_manage_departments)
        self.btn_edit_department.setEnabled(self._can_manage_departments and has_department)
        self.btn_toggle_active.setEnabled(self._can_manage_departments and has_department)


__all__ = ["DepartmentAdminTab"]
