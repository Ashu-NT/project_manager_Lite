from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import QComboBox, QDialog, QLineEdit

from src.api.desktop.platform import (
    PlatformDocumentDesktopApi,
    EmployeeDto,
    PlatformDepartmentDesktopApi,
    PlatformEmployeeDesktopApi,
    PlatformPartyDesktopApi,
    PlatformRuntimeDesktopApi,
    PlatformSiteDesktopApi,
    PlatformUserDesktopApi,
)
from src.core.modules.project_management.domain.tasks.task import Task
from core.modules.project_management.domain.enums import TaskStatus
from tests.ui_runtime_helpers import make_settings_store
from src.ui.platform.dialogs.admin.employees.dialogs import EmployeeEditDialog
from src.ui.platform.workspaces.admin.employees.tab import EmployeeAdminTab
from src.ui.platform.workspaces.admin.documents.tab import DocumentAdminTab
from src.ui.platform.workspaces.admin.modules.tab import ModuleLicensingTab
from src.ui.platform.workspaces.admin.departments.tab import DepartmentAdminTab
from src.ui.platform.dialogs.admin.organizations.dialogs import OrganizationEditDialog
from src.ui.platform.workspaces.admin.organizations.tab import OrganizationAdminTab
from src.ui.platform.workspaces.admin.parties.tab import PartyAdminTab
from src.ui.platform.workspaces.admin.sites.tab import SiteAdminTab
from src.ui.platform.dialogs.admin.users.dialogs import PasswordResetDialog, UserEditDialog
from src.ui.platform.workspaces.admin.users.tab import UserAdminTab
from src.ui.platform.workspaces.control.approvals.tab import ApprovalControlTab
from src.ui.platform.workspaces.control.audit.tab import AuditLogTab
from src.ui.shared.dialogs.login_dialog import LoginDialog
from src.ui.shell.main_window import MainWindow
from ui.modules.project_management.task.task_progress_dialog import TaskProgressDialog


def _platform_site_api(services):
    return PlatformSiteDesktopApi(site_service=services["site_service"])


def _platform_department_api(services):
    return PlatformDepartmentDesktopApi(department_service=services["department_service"])


def _platform_employee_api(services):
    return PlatformEmployeeDesktopApi(employee_service=services["employee_service"])


def _platform_document_api(services):
    return PlatformDocumentDesktopApi(document_service=services["document_service"])


def _platform_party_api(services):
    return PlatformPartyDesktopApi(party_service=services["party_service"])


def _platform_user_api(services):
    return PlatformUserDesktopApi(auth_service=services["auth_service"])


def test_main_window_exposes_admin_tabs_for_auth_manage_runtime(qapp, services, repo_workspace, monkeypatch):
    store = make_settings_store(repo_workspace, prefix="main-window-admin")
    monkeypatch.setattr("src.ui.shell.main_window.MainWindowSettingsStore", lambda: store)
    monkeypatch.setattr(MainWindow, "_run_startup_update_check", lambda self: None)

    window = MainWindow(services)
    labels = [window.tabs.tabText(i) for i in range(window.tabs.count())]

    assert "Projects" in labels
    assert "Register" in labels
    assert "Tasks" in labels
    assert "Collaboration" in labels
    assert "Portfolio" in labels
    assert "Users" in labels
    assert "Employees" in labels
    assert "Organizations" in labels
    assert "Sites" in labels
    assert "Departments" in labels
    assert "Documents" in labels
    assert "Parties" in labels
    assert "Access" in labels
    assert "Security" in labels
    assert "Approvals" in labels
    assert "Audit" in labels
    assert "Support" in labels
    assert "Modules" in labels


def test_user_admin_tab_runtime_enables_edit_and_reset_actions_after_selection(qapp, services):
    tab = UserAdminTab(
        platform_user_api=_platform_user_api(services),
        user_session=services["user_session"],
    )

    assert tab.table.rowCount() >= 1
    assert tab.user_scope_badge.text() == "Account Directory"
    assert tab.user_count_badge.text().endswith("users")
    assert tab.user_active_badge.text().endswith("active")
    assert tab.user_access_badge.text() == "Manage Enabled"
    assert tab.btn_new_user.isEnabled() is True
    assert tab.btn_edit_user.isEnabled() is False
    assert tab.btn_reset_password.isEnabled() is False

    tab.table.selectRow(0)
    tab._sync_actions()

    assert tab.btn_edit_user.isEnabled() is True
    assert tab.btn_reset_password.isEnabled() is True
    assert tab.btn_toggle_active.isEnabled() is True


def test_audit_log_tab_runtime_uses_compact_header_and_updates_badges(qapp, services):
    project = services["project_service"].create_project("Audit Header Project")
    tab = AuditLogTab(
        audit_service=services["audit_service"],
        project_service=services["project_service"],
        task_service=services["task_service"],
        resource_service=services["resource_service"],
        cost_service=services["cost_service"],
        baseline_service=services["baseline_service"],
    )

    assert tab.table.rowCount() >= 1
    assert tab.audit_scope_badge.text() == "Append-only"
    assert tab.audit_project_badge.text() == "All"
    assert tab.audit_count_badge.text().endswith("rows")
    assert tab.audit_date_badge.text() == "All Dates"
    assert tab.btn_refresh.isEnabled() is True


def test_approval_control_tab_runtime_uses_shared_queue_badges(qapp, services):
    project = services["project_service"].create_project("Approval Control Project")
    services["approval_service"].request_change(
        request_type="baseline.create",
        entity_type="baseline",
        entity_id="baseline-1",
        project_id=project.id,
        payload={"name": "Gate Baseline", "project_name": project.name},
    )

    tab = ApprovalControlTab(
        approval_service=services["approval_service"],
        user_session=services["user_session"],
    )

    assert tab.table.rowCount() == 1
    assert tab.approval_scope_badge.text() == "Shared Review"
    assert tab.approval_access_badge.text() == "Decision Enabled"
    assert tab.approval_status_badge.text() == "Pending"
    assert tab.approval_count_badge.text() == "1 requests"
    assert tab.table.item(0, 2).text() == "Project Management"


def test_audit_log_tab_refreshes_when_module_entitlements_change(qapp, services):
    services["project_service"].create_project("Audit Module Toggle Project")
    tab = AuditLogTab(
        audit_service=services["audit_service"],
        project_service=services["project_service"],
        task_service=services["task_service"],
        resource_service=services["resource_service"],
        cost_service=services["cost_service"],
        baseline_service=services["baseline_service"],
    )
    starting_rows = tab.table.rowCount()

    services["module_catalog_service"].set_module_state("project_management", enabled=False)
    qapp.processEvents()

    assert tab.table.rowCount() >= starting_rows
    assert any(
        tab.table.item(row, 2).text() == "module.entitlement.update"
        for row in range(tab.table.rowCount())
    )


def test_module_licensing_tab_runtime_toggles_project_management_enablement(qapp, services):
    tab = ModuleLicensingTab(
        platform_runtime_api=PlatformRuntimeDesktopApi(
            platform_runtime_application_service=services["platform_runtime_application_service"]
        ),
        user_session=services["user_session"],
    )

    assert tab.table.rowCount() == 5
    assert tab.context_badge.text() == "Context: Default Organization"
    assert tab.licensed_badge.text() == "1 licensed"
    assert tab.runtime_badge.text() == "1 runtime"
    assert tab.lifecycle_badge.text() == "0 alerts"

    tab.table.selectRow(0)
    tab._sync_actions()
    assert tab.btn_toggle_license.isEnabled() is True
    assert tab.btn_toggle_enabled.isEnabled() is True
    assert tab.btn_change_status.isEnabled() is True

    tab.toggle_enabled()
    qapp.processEvents()

    assert services["module_catalog_service"].is_enabled("project_management") is False
    assert tab.table.item(0, 4).text() == "No"
    assert tab.table.item(0, 5).text() == "No"

    tab.table.selectRow(0)
    tab.toggle_enabled()
    qapp.processEvents()
    assert services["module_catalog_service"].is_enabled("project_management") is True


def test_module_licensing_tab_runtime_changes_lifecycle_status(qapp, services, monkeypatch):
    tab = ModuleLicensingTab(
        platform_runtime_api=PlatformRuntimeDesktopApi(
            platform_runtime_application_service=services["platform_runtime_application_service"]
        ),
        user_session=services["user_session"],
    )
    tab.table.selectRow(0)
    tab._sync_actions()
    monkeypatch.setattr(
        "src.ui.platform.workspaces.admin.modules.tab.QInputDialog.getItem",
        lambda *_args, **_kwargs: ("Suspended", True),
    )

    tab.change_status()
    qapp.processEvents()

    assert tab.table.item(0, 2).text() == "Suspended"
    assert tab.table.item(0, 4).text() == "No"
    assert tab.table.item(0, 5).text() == "No"
    assert tab.lifecycle_badge.text() == "1 alerts"


def test_organization_admin_tab_runtime_bootstraps_default_profile(qapp, services):
    tab = OrganizationAdminTab(
        platform_runtime_api=PlatformRuntimeDesktopApi(
            platform_runtime_application_service=services["platform_runtime_application_service"]
        ),
        user_session=services["user_session"],
    )

    assert tab.table.rowCount() >= 1
    assert tab.organization_scope_badge.text() == "Install Profile"
    assert tab.organization_count_badge.text().endswith("organizations")
    assert tab.organization_active_badge.text() == "Default Organization"
    assert tab.organization_access_badge.text() == "Manage Enabled"
    assert tab.btn_new_organization.isEnabled() is True
    assert tab.btn_edit_organization.isEnabled() is False
    assert tab.btn_set_active.isEnabled() is False


def test_organization_edit_dialog_defaults_initial_module_selection(qapp, services):
    platform_runtime_api = PlatformRuntimeDesktopApi(
        platform_runtime_application_service=services["platform_runtime_application_service"]
    )
    modules_result = platform_runtime_api.list_modules()
    assert modules_result.ok is True
    assert modules_result.data is not None

    dialog = OrganizationEditDialog(
        available_modules=modules_result.data,
    )

    assert dialog.initial_module_codes == ["project_management"]


def test_site_admin_tab_runtime_bootstraps_active_org_context(qapp, services):
    tab = SiteAdminTab(
        platform_site_api=_platform_site_api(services),
        user_session=services["user_session"],
    )

    assert tab.table.rowCount() == 0
    assert tab.site_context_badge.text() == "Context: Default Organization"
    assert tab.site_count_badge.text() == "0 sites"
    assert tab.site_active_badge.text() == "0 active"
    assert tab.site_access_badge.text() == "Manage Enabled"
    assert tab.btn_new_site.isEnabled() is True
    assert tab.btn_edit_site.isEnabled() is False
    assert tab.btn_toggle_active.isEnabled() is False


def test_department_admin_tab_runtime_bootstraps_active_org_context(qapp, services):
    tab = DepartmentAdminTab(
        platform_department_api=_platform_department_api(services),
        platform_site_api=_platform_site_api(services),
        user_session=services["user_session"],
    )

    assert tab.table.rowCount() == 0
    assert tab.department_context_badge.text() == "Context: Default Organization"
    assert tab.department_count_badge.text() == "0 departments"
    assert tab.department_active_badge.text() == "0 active"
    assert tab.department_access_badge.text() == "Manage Enabled"
    assert tab.btn_new_department.isEnabled() is True
    assert tab.btn_edit_department.isEnabled() is False
    assert tab.btn_toggle_active.isEnabled() is False


def test_department_admin_tab_shows_default_location_reference(qapp, services):
    site = services["site_service"].create_site(site_code="DEPT-MNT", name="Department Plant")
    location = services["maintenance_location_service"].create_location(
        site_id=site.id,
        location_code="shop-a",
        name="Shop A",
    )
    services["department_service"].create_department(
        department_code="OPS",
        name="Operations",
        site_id=site.id,
        default_location_id=location.id,
    )

    tab = DepartmentAdminTab(
        platform_department_api=_platform_department_api(services),
        platform_site_api=_platform_site_api(services),
        user_session=services["user_session"],
    )

    assert tab.table.rowCount() == 1
    assert tab.table.item(0, 3).text() == "SHOP-A - Shop A"


def test_document_admin_tab_runtime_bootstraps_active_org_context(qapp, services):
    tab = DocumentAdminTab(
        platform_document_api=_platform_document_api(services),
        user_session=services["user_session"],
    )

    assert tab.table.rowCount() == 0
    assert tab.document_context_badge.text() == "Context: Default Organization"
    assert tab.document_count_badge.text() == "0 documents"
    assert tab.document_active_badge.text() == "0 active"
    assert tab.document_access_badge.text() == "Manage Enabled"
    assert tab.btn_new_document.isEnabled() is True
    assert tab.btn_edit_document.isEnabled() is False
    assert tab.btn_toggle_active.isEnabled() is False
    assert tab.btn_add_link.isEnabled() is False


def test_party_admin_tab_runtime_bootstraps_active_org_context(qapp, services):
    tab = PartyAdminTab(
        platform_party_api=_platform_party_api(services),
        user_session=services["user_session"],
    )

    assert tab.table.rowCount() == 0
    assert tab.party_context_badge.text() == "Context: Default Organization"
    assert tab.party_count_badge.text() == "0 parties"
    assert tab.party_active_badge.text() == "0 active"
    assert tab.party_access_badge.text() == "Manage Enabled"
    assert tab.btn_new_party.isEnabled() is True
    assert tab.btn_edit_party.isEnabled() is False
    assert tab.btn_toggle_active.isEnabled() is False


def test_employee_admin_tab_runtime_bootstraps_shared_reference_badge_and_links(qapp, services):
    tab = EmployeeAdminTab(
        platform_employee_api=_platform_employee_api(services),
        platform_site_api=_platform_site_api(services),
        platform_department_api=_platform_department_api(services),
        user_session=services["user_session"],
    )

    assert tab.employee_reference_badge.text() == "Shared refs: 0 sites / 0 departments"
    assert tab.btn_open_sites.isEnabled() is True
    assert tab.btn_open_departments.isEnabled() is True

    site = services["site_service"].create_site(site_code="BER", name="Berlin Plant")
    services["department_service"].create_department(
        department_code="OPS",
        name="Operations",
        site_id=site.id,
    )
    qapp.processEvents()

    assert tab.employee_reference_badge.text() == "Shared refs: 1 sites / 1 departments"


def test_employee_edit_dialog_prefers_shared_reference_selectors_but_keeps_legacy_text(qapp):
    employee = EmployeeDto(
        id="employee-1",
        employee_code="EMP-1",
        full_name="Alex Example",
        department_id=None,
        department="Legacy Department",
        site_id=None,
        site_name="Legacy Site",
        title="",
        employment_type="FULL_TIME",
        email=None,
        phone=None,
        is_active=True,
        version=1,
    )
    dialog = EmployeeEditDialog(
        employee=employee,
        department_options=[("Operations", "department-ops")],
        site_options=[("Berlin Plant", "site-ber")],
    )

    assert isinstance(dialog.department_combo, QComboBox)
    assert isinstance(dialog.site_name_combo, QComboBox)
    assert dialog.department == "Legacy Department"
    assert dialog.department_id is None
    assert dialog.site_name == "Legacy Site"
    assert dialog.site_id is None

    dialog.department_combo.setEditText("Operations")
    dialog.site_name_combo.setEditText("Berlin Plant")

    assert dialog.department == "Operations"
    assert dialog.department_id == "department-ops"
    assert dialog.site_name == "Berlin Plant"
    assert dialog.site_id == "site-ber"


def test_organization_admin_tab_creates_organization_with_initial_module_mix(qapp, services, monkeypatch):
    class _FakeDialog:
        organization_code = "OPS"
        display_name = "Operations Hub"
        timezone_name = "Africa/Lagos"
        base_currency = "USD"
        is_active = False
        initial_module_codes: list[str] = []

        def __init__(self, *args, **kwargs):
            pass

        def exec(self):
            return QDialog.Accepted

    monkeypatch.setattr("src.ui.platform.workspaces.admin.organizations.tab.OrganizationEditDialog", _FakeDialog)
    tab = OrganizationAdminTab(
        platform_runtime_api=PlatformRuntimeDesktopApi(
            platform_runtime_application_service=services["platform_runtime_application_service"]
        ),
        user_session=services["user_session"],
    )

    tab.create_organization()

    created = next(
        row for row in services["organization_service"].list_organizations() if row.organization_code == "OPS"
    )
    services["organization_service"].set_active_organization(created.id)

    assert services["module_catalog_service"].current_context_label() == "Operations Hub"
    assert services["module_catalog_service"].is_enabled("project_management") is False


def test_login_dialog_runtime_toggles_password_and_signs_in(qapp, anonymous_services):
    auth_service = anonymous_services["auth_service"]
    user_session = anonymous_services["user_session"]
    dialog = LoginDialog(auth_service=auth_service, user_session=user_session)

    assert dialog.password_input.echoMode() == QLineEdit.Password
    dialog.btn_toggle_password.setChecked(True)
    assert dialog.password_input.echoMode() == QLineEdit.Normal
    assert dialog.btn_toggle_password.text() == "Hide"

    dialog.username_input.setText("admin")
    dialog.password_input.setText("ChangeMe123!")
    dialog._try_sign_in()

    assert dialog.result() == QDialog.Accepted
    assert dialog.principal is not None
    assert dialog.principal.username == "admin"


def test_password_reset_dialog_runtime_validates_match_and_accepts(qapp, monkeypatch):
    warnings: list[str] = []
    monkeypatch.setattr(
        "src.ui.platform.dialogs.admin.users.dialogs.QMessageBox.warning",
        lambda _parent, _title, message: warnings.append(message),
    )
    dialog = PasswordResetDialog(username="alice")

    dialog.btn_toggle_password.setChecked(True)
    assert dialog.password_input.echoMode() == QLineEdit.Normal
    assert dialog.confirm_password_input.echoMode() == QLineEdit.Normal

    dialog.password_input.setText("StrongPass123")
    dialog.confirm_password_input.setText("Mismatch123")
    dialog._validate_and_accept()
    assert warnings[-1] == "Password and confirm password must match."
    assert dialog.result() != QDialog.Accepted

    dialog.confirm_password_input.setText("StrongPass123")
    dialog._validate_and_accept()
    assert dialog.result() == QDialog.Accepted


def test_user_edit_dialog_runtime_validates_email(qapp, monkeypatch):
    warnings: list[str] = []
    monkeypatch.setattr(
        "src.ui.platform.dialogs.admin.users.dialogs.QMessageBox.warning",
        lambda _parent, _title, message: warnings.append(message),
    )
    dialog = UserEditDialog(username="alice", display_name="Alice", email="alice@example.com")

    dialog.email_input.setText("not-an-email")
    dialog._validate_and_accept()
    assert warnings[-1] == "Invalid email format."
    assert dialog.result() != QDialog.Accepted

    dialog.email_input.setText("updated@example.com")
    dialog._validate_and_accept()
    assert dialog.result() == QDialog.Accepted


def test_task_progress_dialog_runtime_supports_status_checkbox_update(qapp, monkeypatch):
    task = Task.create(
        project_id="project-1",
        name="Progress Task",
        start_date=date(2026, 3, 1),
        duration_days=2,
        status=TaskStatus.TODO,
    )
    dialog = TaskProgressDialog(task=task)
    monkeypatch.setattr(dialog, "_prompt_iso_date", lambda *_args, **_kwargs: date(2026, 3, 2))

    dialog.status_check.setChecked(True)
    dialog.status_combo.setCurrentIndex(dialog.status_combo.findData(TaskStatus.IN_PROGRESS))
    payload = dialog.build_payload()

    assert dialog.status_set is True
    assert payload is not None
    assert payload["status"] == TaskStatus.IN_PROGRESS
    assert payload["actual_start"] == date(2026, 3, 2)
